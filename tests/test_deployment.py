"""
Deployment verification tests
"""

import os
import pytest
import requests
import tempfile
import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from services.s3_service import S3ClientManager

# Load environment variables from .env file
load_dotenv()

s3_client = None
if os.getenv('AWS_REGION') and os.getenv('S3_BUCKET_NAME') and os.getenv('COGNITO_IDENTITY_POOL_ID'):
    s3_manager = S3ClientManager.get_instance()
    s3_client = s3_manager.get_client()

@pytest.fixture(autouse=True)
def skip_if_no_s3_env_vars():
    if not (os.getenv('AWS_REGION') and os.getenv('S3_BUCKET_NAME') and os.getenv('COGNITO_IDENTITY_POOL_ID')):
        pytest.skip("Skipping S3 tests because environment variables are not set.")

def test_health_check(api_url):
    """Test health check endpoint"""
    response = requests.get(f"{api_url}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_analyze_endpoint(api_url):
    """Test direct audio analysis endpoint with a generated test file"""
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
                    f"{api_url}/api/v1/analyze",
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

def test_recording_session_flow(api_url):
    """Test complete recording session flow: start -> analyze"""
    # Start recording session
    start_data = {
        "device_name": "Test Device",
        "ip_address": "192.168.1.1",
        "audio_format": "wav"
    }
    response = requests.post(f"{api_url}/api/v1/recording-session/start", json=start_data)
    assert response.status_code == 200
    session_data = response.json()
    assert "recording_session_id" in session_data
    session_id = session_data["recording_session_id"]
    
    # Create a test audio file
    sample_rate = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * 440 * t)
    
    # Create temporary WAV file
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        sf.write(temp_file.name, audio_data, sample_rate)
        
        try:
            # Test file upload and analysis
            with open(temp_file.name, 'rb') as f:
                files = {'file': ('test.wav', f, 'audio/wav')}
                response = requests.post(
                    f"{api_url}/api/v1/recording-session/{session_id}/analyze",
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
            
        finally:
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

def test_invalid_file(api_url):
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
                    f"{api_url}/api/v1/analyze",
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

def test_s3_token_lifecycle(api_url):
    """Test S3 token management endpoints"""
    # Check initial token status
    response = requests.get(f"{api_url}/api/v1/s3-token/status")
    assert response.status_code == 200
    status = response.json()
    assert status["status"] in ["active", "expired"]
    
    if status["status"] == "expired":
        # If token is expired, refresh it
        response = requests.post(f"{api_url}/api/v1/s3-token/refresh")
        assert response.status_code == 200
        status = response.json()
        assert status["status"] == "active"
        assert status["expires_in_seconds"] > 0
        assert status["expiry_time"] is not None
    
    # Force token expiration
    response = requests.post(f"{api_url}/api/v1/s3-token/expire")
    assert response.status_code == 200
    status = response.json()
    assert status["status"] == "expired"
    assert status["expires_in_seconds"] == 0
    
    # Refresh expired token
    response = requests.post(f"{api_url}/api/v1/s3-token/refresh")
    assert response.status_code == 200
    status = response.json()
    assert status["status"] == "active"
    assert status["expires_in_seconds"] > 0
    assert status["expiry_time"] is not None
    
    # Verify token status matches
    response = requests.get(f"{api_url}/api/v1/s3-token/status")
    assert response.status_code == 200
    verify_status = response.json()
    assert verify_status["status"] == "active"
    assert verify_status["expiry_time"] == status["expiry_time"]
