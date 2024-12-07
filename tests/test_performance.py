"""
Performance tests for the API
"""

import os
import time
import pytest
import requests
import numpy as np
import soundfile as sf
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict

API_URL = os.getenv('API_URL', 'https://audio-analyzer-api-af6843ebf910.herokuapp.com')

def generate_test_audio(duration: float = 1.0, sample_rate: int = 16000) -> str:
    """Generate a test audio file and return its path"""
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * 440 * t)
    
    # Create temporary WAV file
    import tempfile
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    sf.write(temp_file.name, audio_data, sample_rate)
    return temp_file.name

def measure_response_time() -> Dict:
    """Measure API response time for a single request"""
    audio_file = generate_test_audio()
    try:
        start_time = time.time()
        with open(audio_file, 'rb') as f:
            response = requests.post(
                f"{API_URL}/api/v1/analyze",
                files={'file': ('test.wav', f, 'audio/wav')}
            )
        end_time = time.time()
        
        return {
            'response_time': end_time - start_time,
            'status_code': response.status_code
        }
    finally:
        if os.path.exists(audio_file):
            os.unlink(audio_file)

def test_api_response_time():
    """Test API response time is within acceptable limits"""
    result = measure_response_time()
    
    # Response time should be under 5 seconds
    assert result['response_time'] < 5.0
    assert result['status_code'] == 200

def test_concurrent_requests():
    """Test API performance under concurrent load"""
    NUM_REQUESTS = 5
    MAX_WORKERS = 3
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(lambda _: measure_response_time(), range(NUM_REQUESTS)))
    
    # Analyze results
    response_times = [r['response_time'] for r in results]
    status_codes = [r['status_code'] for r in results]
    
    # All requests should succeed
    assert all(code == 200 for code in status_codes)
    
    # Calculate statistics
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    
    # Performance assertions
    assert avg_response_time < 7.0  # Average response time under 7 seconds
    assert max_response_time < 10.0  # Max response time under 10 seconds

def test_memory_usage():
    """Test memory usage by processing multiple files sequentially"""
    NUM_REQUESTS = 3
    memory_usage = []
    
    import psutil
    process = psutil.Process()
    
    for _ in range(NUM_REQUESTS):
        # Measure memory before request
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make request
        result = measure_response_time()
        assert result['status_code'] == 200
        
        # Measure memory after request
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_usage.append(mem_after - mem_before)
        
        # Small delay between requests
        time.sleep(1)
    
    # Check memory usage patterns
    # Memory growth should not be excessive
    assert max(memory_usage) < 100  # Less than 100MB growth per request
