"""
Tests for utility functions
"""

import os
import pytest
from audio_analyzer.utils import get_media_info, cleanup_temp_file, create_temp_wav

def test_get_media_info_valid_file(sample_wav_file):
    """Test getting media info from a valid audio file"""
    result = get_media_info(sample_wav_file)
    assert result is not None
    assert 'streams' in result
    assert len(result['streams']) > 0
    assert 'codec_type' in result['streams'][0]

def test_get_media_info_invalid_file():
    """Test getting media info from an invalid file"""
    result = get_media_info('nonexistent_file.wav')
    assert result is None

def test_cleanup_temp_file():
    """Test cleanup of temporary WAV file"""
    # Create a temporary file
    temp_file = create_temp_wav()
    assert os.path.exists(temp_file)
    
    # Clean it up
    cleanup_temp_file(temp_file)
    assert not os.path.exists(temp_file)

def test_cleanup_temp_file_nonexistent():
    """Test cleanup of nonexistent file"""
    cleanup_temp_file('nonexistent_file.wav')  # Should not raise any exception

def test_create_temp_wav():
    """Test creation of temporary WAV file"""
    temp_file = create_temp_wav()
    try:
        assert os.path.exists(temp_file)
        assert temp_file.endswith('.wav')
    finally:
        cleanup_temp_file(temp_file)