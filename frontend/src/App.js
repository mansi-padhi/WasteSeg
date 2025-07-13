import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = 'http://localhost:5000';
const ALLOWED_FILE_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
const MAX_FILE_SIZE = 16 * 1024 * 1024; // 16MB

function App() {
  const [file, setFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [scores, setScores] = useState(null);
  const [dominantType, setDominantType] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const validateFile = (file) => {
    if (!file) {
      return "Please select a file";
    }

    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      return "Please select a valid image file (JPEG, PNG, GIF, WebP)";
    }

    if (file.size > MAX_FILE_SIZE) {
      return "File size must be less than 16MB";
    }

    return null;
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    
    // Reset previous states
    setError('');
    setScores(null);
    setDominantType('');
    
    if (!selectedFile) {
      setFile(null);
      setImagePreview(null);
      return;
    }

    const validationError = validateFile(selectedFile);
    if (validationError) {
      setError(validationError);
      setFile(null);
      setImagePreview(null);
      return;
    }

    setFile(selectedFile);
    
    // Create image preview
    const reader = new FileReader();
    reader.onload = (e) => {
      setImagePreview(e.target.result);
    };
    reader.readAsDataURL(selectedFile);
  };

  const categorizeWaste = (data) => {
    // Define waste categories
    const biodegradable = ["paper", "cardboard", "organic"];
    const nonBiodegradable = ["plastic", "metal", "glass"];
    const organic = ["trash", "food", "compost"];

    let result = {
      biodegradable: 0,
      nonBiodegradable: 0,
      organic: 0,
    };

    // Categorize predictions
    for (const [label, value] of Object.entries(data)) {
      const lowerLabel = label.toLowerCase();
      
      if (biodegradable.some(cat => lowerLabel.includes(cat))) {
        result.biodegradable += value;
      } else if (nonBiodegradable.some(cat => lowerLabel.includes(cat))) {
        result.nonBiodegradable += value;
      } else if (organic.some(cat => lowerLabel.includes(cat))) {
        result.organic += value;
      }
    }

    // Find dominant category
    const maxVal = Math.max(...Object.values(result));
    const dominant = Object.keys(result).find(key => result[key] === maxVal);

    return { result, dominant };
  };

  const handleUpload = async () => {
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      return;
    }

    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_BASE_URL}/predict`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 30000, // 30 second timeout
      });

      const data = response.data;
      console.log('Prediction results:', data);

      const { result, dominant } = categorizeWaste(data);

      setScores(result);
      setDominantType(dominant);

    } catch (err) {
      console.error('Upload error:', err);
      
      if (err.code === 'ECONNABORTED') {
        setError('Request timeout. Please try again.');
      } else if (err.response) {
        // Server responded with error
        const errorMessage = err.response.data?.error || 'Server error occurred';
        setError(`Error: ${errorMessage}`);
      } else if (err.request) {
        // Network error
        setError('Network error. Please check if the server is running.');
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setImagePreview(null);
    setScores(null);
    setDominantType('');
    setError('');
    // Reset file input
    const fileInput = document.getElementById('file-input');
    if (fileInput) fileInput.value = '';
  };

  return (
    <div className="App">
      <div className="container">
        <h1>🗂️ Waste Classifier</h1>
        <p>Upload an image to classify waste type</p>

        <div className="upload-section">
          <input
            id="file-input"
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            disabled={loading}
          />
          
          {imagePreview && (
            <div className="image-preview">
              <img src={imagePreview} alt="Preview" />
            </div>
          )}

          <div className="button-group">
            <button 
              onClick={handleUpload} 
              disabled={!file || loading}
              className="predict-btn"
            >
              {loading ? 'Analyzing...' : 'Upload & Predict'}
            </button>
            
            <button 
              onClick={resetForm} 
              disabled={loading}
              className="reset-btn"
            >
              Reset
            </button>
          </div>
        </div>

        {error && (
          <div className="error-message">
            <span>⚠️ {error}</span>
          </div>
        )}

        {loading && (
          <div className="loading">
            <div className="spinner"></div>
            <p>Analyzing your image...</p>
          </div>
        )}

        {scores && (
          <div className="results">
            <h3>🎯 Classification Results</h3>
            <div className="dominant-type">
              <strong>Dominant Type: {dominantType.charAt(0).toUpperCase() + dominantType.slice(1)}</strong>
            </div>

            <div className="score-bars">
              <div className="score-item">
                <div className="score-header">
                  <span>🌱 Biodegradable</span>
                  <span>{scores.biodegradable.toFixed(1)}%</span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill green" 
                    style={{ width: `${Math.max(scores.biodegradable, 5)}%` }}
                  ></div>
                </div>
              </div>

              <div className="score-item">
                <div className="score-header">
                  <span>🏭 Non-Biodegradable</span>
                  <span>{scores.nonBiodegradable.toFixed(1)}%</span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill red" 
                    style={{ width: `${Math.max(scores.nonBiodegradable, 5)}%` }}
                  ></div>
                </div>
              </div>

              <div className="score-item">
                <div className="score-header">
                  <span>🍂 Organic</span>
                  <span>{scores.organic.toFixed(1)}%</span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill yellow" 
                    style={{ width: `${Math.max(scores.organic, 5)}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;