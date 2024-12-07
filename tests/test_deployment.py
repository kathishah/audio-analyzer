"""
Deployment verification tests
"""

import os
import pytest
import requests
import tempfile
import numpy as np
import soundfile as sf

# API base URL
API_URL = os.getenv('API_URL', 'https://audio-analyzer-api-af6843ebf910.herokuapp.com')

def test_health_check():
    """Test health check endpoint"""
    response = requests.get(f"{API_URL}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_api_docs():
    """Test API documentation endpoint"""
    response = requests.get(f"{API_URL}/docs")
    assert response.status_code == 200

def test_analyze_endpoint():
    """Test audio analysis endpoint with a generated test file"""
    # Create a simple test audio file
    sample_rate = 16000
    duration = 1.0  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
    
    # Create temporary WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        sf.write(temp_file.name, audio_data, sample_rate)
        
        try:
            # Test file upload and analysis
            with open(temp_file.name, 'rb') as f:
                files = {'file': ('test.wav', f, 'audio/wav')}
                response = requests.post(
                    f"{API_URL}/api/v1/analyze",
                    files=files
                )
            
            # Check response
            assert response.status_code == 200
            result = response.json()
            
            # Verify response structure
            assert 'pesq_score' in result
            assert 'quality_category' in result
            assert 'snr_db' in result
            assert 'sample_rate' in result
            
            # Verify data types
            assert isinstance(result['pesq_score'], float)
            assert isinstance(result['quality_category'], str)
            assert isinstance(result['snr_db'], float)
            assert isinstance(result['sample_rate'], int)
            
            # Verify sample rate matches input
            assert result['sample_rate'] == sample_rate
            
        finally:
            # Cleanup
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

def test_invalid_file():
    """Test error handling for invalid file upload"""
    # Create an invalid file
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
        temp_file.write(b"This is not an audio file")
        temp_file.close()
        
        try:
            # Test file upload
            with open(temp_file.name, 'rb') as f:
                files = {'file': ('test.txt', f, 'text/plain')}
                response = requests.post(
                    f"{API_URL}/api/v1/analyze",
                    files=files
                )
            
            # Check response
            assert response.status_code == 500
            result = response.json()
            assert 'detail' in result
            
        finally:
            # Cleanup
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
