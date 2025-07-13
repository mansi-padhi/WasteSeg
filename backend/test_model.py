import torch
from transformers import ViTFeatureExtractor, ViTForImageClassification
from PIL import Image
import numpy as np

def test_model():
    print("Loading model...")
    processor = ViTFeatureExtractor.from_pretrained('wasteseg')
    model = ViTForImageClassification.from_pretrained('wasteseg')
    
    print("Model loaded successfully!")
    print(f"Model config id2label: {model.config.id2label}")
    print(f"Model config label2id: {model.config.label2id}")
    
    # Create a dummy image (random noise)
    dummy_image = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
    
    print("Processing dummy image...")
    inputs = processor(images=dummy_image, return_tensors="pt")
    
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=1)[0]
    
    print("Raw logits:", outputs.logits)
    print("Probabilities:", probs)
    
    # Convert predictions to result dictionary - THIS IS THE BUGGY CODE
    result = {}
    for idx, prob in enumerate(probs):
        # Handle missing id2label mapping
        if hasattr(model.config, 'id2label') and str(idx) in model.config.id2label:
            label = model.config.id2label[str(idx)]
        else:
            label = f"class_{idx}"
        
        result[label] = round(prob.item() * 100, 2)
    
    print("Final result (buggy):", result)
    
    # CORRECTED VERSION
    result_corrected = {}
    for idx, prob in enumerate(probs):
        # The id2label mapping uses string keys
        label = model.config.id2label[str(idx)]
        result_corrected[label] = round(prob.item() * 100, 2)
    
    print("Final result (corrected):", result_corrected)
    
    # Check if all probabilities are the same
    prob_values = list(result_corrected.values())
    if len(set(prob_values)) == 1:
        print("WARNING: All probabilities are the same! This indicates a problem with the model.")
    else:
        print("Probabilities are different - model seems to be working.")
    
    return result_corrected

if __name__ == "__main__":
    test_model() 