"""
Deployment verification tests
"""

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

import os
import pytest
import requests
import tempfile
import numpy as np
import soundfile as sf
from services.s3_service import upload_file_to_s3, s3_client

def test_health_check(api_url):
    """Test health check endpoint"""
    response = requests.get(f"{api_url}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_api_docs(api_url):
    """Test API documentation endpoint"""
    response = requests.get(f"{api_url}/docs")
    assert response.status_code == 200

def test_analyze_endpoint(api_url):
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

@pytest.mark.s3
def test_upload_file_to_s3():
    # Arrange
    file_path = 'test_file.txt'
    content_type = 'text/plain'
    expected_bucket = os.getenv('S3_BUCKET_NAME', 'crispvoice-audio-recordings')

    # Create a test file
    with open(file_path, 'w') as f:
        f.write('This is a test file.')

    # Act
    result_url = upload_file_to_s3(file_path, content_type)

    # Assert the result URL
    expected_url_prefix = f"https://{expected_bucket}.s3.{os.getenv('AWS_REGION', 'us-west-1')}.amazonaws.com/"
    assert result_url.startswith(expected_url_prefix), f"Unexpected result URL: {result_url}"

    # Verify the file is accessible in S3
    file_name = result_url.split('/')[-1]
    response = s3_client.list_objects_v2(Bucket=expected_bucket, Prefix=file_name)
    file_exists = 'Contents' in response and any(obj['Key'] == file_name for obj in response['Contents'])

    assert file_exists, "File was not uploaded to S3."

    # Cleanup
    file_name = result_url.split('/')[-1]
    s3_client.delete_object(Bucket=expected_bucket, Key=file_name)
    os.remove(file_path)
