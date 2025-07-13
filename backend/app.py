from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import ViTFeatureExtractor, ViTForImageClassification
from PIL import Image
import torch
import os
import uuid
import logging
from werkzeug.utils import secure_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])

# Configuration
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB
MODEL_DIR = "wasteseg"

# Create upload directory
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Global variables for model
processor = None
model = None

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_model():
    """Load the model and processor"""
    global processor, model
    try:
        logger.info("Loading model and processor...")
        processor = ViTFeatureExtractor.from_pretrained(MODEL_DIR)
        model = ViTForImageClassification.from_pretrained(MODEL_DIR)
        logger.info("Model loaded successfully!")
        return True
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return False

def cleanup_file(filepath):
    """Remove uploaded file after processing"""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Cleaned up file: {filepath}")
    except Exception as e:
        logger.warning(f"Could not remove file {filepath}: {e}")

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "message": "WasteSeg API is running",
        "endpoints": {
            "predict": "POST /predict - Upload image for waste classification",
            "health": "GET /health - Check API health"
        }
    })

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    model_status = "loaded" if model is not None else "not loaded"
    return jsonify({
        "status": "healthy",
        "model_status": model_status
    })

@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    """Predict waste type from uploaded image"""
    
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return '', 200
    
    # Check if model is loaded
    if model is None or processor is None:
        return jsonify({"error": "Model not loaded. Please check server logs."}), 500
    
    # Validate file in request
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    # Check file extension
    if not allowed_file(file.filename):
        return jsonify({
            "error": f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400
    
    # Check file size
    if request.content_length > MAX_FILE_SIZE:
        return jsonify({"error": "File too large. Maximum size is 16MB"}), 400
    
    # Generate unique filename
    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
    
    try:
        # Save file
        file.save(filepath)
        logger.info(f"File saved: {filepath}")
        
        # Open and process image
        try:
            image = Image.open(filepath).convert("RGB")
        except Exception as e:
            cleanup_file(filepath)
            return jsonify({"error": "Invalid image file"}), 400
        
        # Process image with model
        inputs = processor(images=image, return_tensors="pt")
        
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=1)[0]
        
        # Convert predictions to result dictionary
        result = {}
        for idx, prob in enumerate(probs):
            # id2label uses integer keys
            if hasattr(model.config, 'id2label') and idx in model.config.id2label:
                label = model.config.id2label[idx]
            else:
                label = f"class_{idx}"
            result[label] = round(prob.item() * 100, 2)
        
        # Clean up uploaded file
        cleanup_file(filepath)
        
        logger.info(f"Prediction successful: {result}")
        return jsonify(result)
        
    except Exception as e:
        # Clean up file in case of error
        cleanup_file(filepath)
        logger.error(f"Prediction error: {e}")
        return jsonify({"error": "Prediction failed. Please try again."}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large"}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

if __name__ == '__main__':
    # Load model on startup
    if not load_model():
        logger.error("Failed to load model. Exiting...")
        exit(1)
    
    # Configure Flask app
    app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE
    
    logger.info("Starting Flask application...")
    app.run(debug=True, host='0.0.0.0', port=5000)