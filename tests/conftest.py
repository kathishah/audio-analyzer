"""
Pytest configuration and fixtures
"""

import os
import pytest
import numpy as np
import soundfile as sf
import tempfile
from audio_analyzer import AudioAnalyzer

@pytest.fixture
def audio_analyzer():
    """Fixture to provide an AudioAnalyzer instance"""
    return AudioAnalyzer()

@pytest.fixture
def sample_wav_file():
    """
    Fixture to create a temporary WAV file for testing
    Returns the path to the temporary file
    """
    # Create a simple sine wave
    sample_rate = 16000
    duration = 1.0  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration))
    audio_data = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
    
    # Create temporary WAV file
    temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    sf.write(temp_file.name, audio_data, sample_rate)
    
    yield temp_file.name
    
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)

@pytest.fixture
def mock_media_info():
    """Fixture to provide mock media info data"""
    return {
        "streams": [
            {
                "codec_type": "audio",
                "sample_rate": "16000",
                "channels": 1
            }
        ]
    }

@pytest.fixture
def test_files_dir():
    """Fixture to provide the path to test resource files"""
    return os.path.join(os.path.dirname(__file__), 'resources')