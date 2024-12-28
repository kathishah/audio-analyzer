"""
Tests for AudioAnalyzer class
"""

import os
import pytest
import magic
import numpy as np
from unittest.mock import patch, MagicMock
from audio_analyzer.analyzer import AudioAnalyzer

def test_categorize_pesq():
    """Test PESQ score categorization"""
    analyzer = AudioAnalyzer()
    
    assert analyzer.categorize_pesq(0.5) == "Poor Quality"
    assert analyzer.categorize_pesq(1.5) == "Fair Quality"
    assert analyzer.categorize_pesq(2.5) == "Good Quality"
    assert analyzer.categorize_pesq(3.5) == "Excellent Quality"
    assert analyzer.categorize_pesq(4.5) == "Outstanding Quality"

def test_convert_to_wav_already_wav(audio_analyzer, sample_wav_file, mocker):
    """Test conversion when file is already WAV"""
    mock_magic = mocker.patch('magic.Magic')
    mock_magic.return_value.from_file.return_value = 'audio/x-wav'
    
    result = audio_analyzer.convert_to_wav(sample_wav_file)
    assert result == sample_wav_file

def test_convert_to_wav_webm(audio_analyzer, sample_wav_file, mocker):
    """Test conversion from WebM to WAV"""
    # Mock magic to return video/webm
    mock_magic = mocker.patch('magic.Magic')
    mock_magic.return_value.from_file.return_value = 'video/webm'
    
    # Mock get_media_info to return audio-only streams
    mock_media_info = {
        'streams': [{'codec_type': 'audio'}]
    }
    mocker.patch('audio_analyzer.utils.get_media_info', return_value=mock_media_info)
    
    # Mock AudioSegment
    mock_audio_segment = mocker.patch('pydub.AudioSegment.from_file')
    mock_audio_segment.return_value.export.return_value = None
    
    try:
        result = audio_analyzer.convert_to_wav(sample_wav_file)
        assert result.endswith('.wav')
    finally:
        if result != sample_wav_file and os.path.exists(result):
            os.unlink(result)

def test_convert_to_wav_invalid_format(audio_analyzer, mocker):
    """Test conversion with invalid format"""
    mock_magic = mocker.patch('magic.Magic')
    mock_magic.return_value.from_file.return_value = 'application/pdf'
    
    with pytest.raises(Exception) as exc_info:
        audio_analyzer.convert_to_wav('test.pdf')

def test_analyze_audio_valid_file(audio_analyzer, sample_wav_file, mocker):
    """Test analysis of a valid audio file"""
    # Mock PESQ calculation
    mocker.patch('audio_analyzer.analyzer.pesq', return_value=3.5)
    
    results = audio_analyzer.analyze_audio(sample_wav_file)
    
    assert results is not None
    assert 'pesq_score' in results
    assert 'quality_category' in results
    assert 'snr_db' in results
    assert 'sample_rate' in results
    
    assert isinstance(results['pesq_score'], float)
    assert isinstance(results['quality_category'], str)
    assert isinstance(results['snr_db'], float)
    assert isinstance(results['sample_rate'], int)
    
    # Check specific values
    assert results['pesq_score'] == 3.5
    assert results['quality_category'] == "Excellent Quality"
    assert results['sample_rate'] == 16000

def test_analyze_audio_invalid_file(audio_analyzer):
    """Test analysis of an invalid file"""
    with pytest.raises(FileNotFoundError):
        audio_analyzer.analyze_audio('nonexistent_file.wav')

def test_analyze_audio_stereo_conversion(audio_analyzer, mocker):
    """Test stereo to mono conversion during analysis"""
    # Create mock stereo audio data using actual numpy array
    mock_audio = np.random.random((1000, 2)).astype(np.float32)
    mono_audio = np.random.random(1000).astype(np.float32)  # Simulated mono audio
    
    # Mock soundfile.read to return stereo data
    mocker.patch('soundfile.read', return_value=(mock_audio, 16000))
    
    # Create a mock for numpy.mean that handles both stereo conversion and power calculation
    original_mean = np.mean
    def mock_mean(*args, **kwargs):
        if len(args) > 0 and isinstance(args[0], np.ndarray):
            if len(args[0].shape) > 1 and 'axis' in kwargs and kwargs['axis'] == 1:
                # This is the stereo to mono conversion
                return mono_audio
            else:
                # This is for power calculations (SNR)
                return 0.5
        return original_mean(*args, **kwargs)
    
    mean_mock = mocker.patch('numpy.mean', side_effect=mock_mean)
    
    # Mock PESQ calculation
    mocker.patch('audio_analyzer.analyzer.pesq', return_value=3.5)
    
    # Mock file type check
    mock_magic = mocker.patch('magic.Magic')
    mock_magic.return_value.from_file.return_value = 'audio/x-wav'
    
    results = audio_analyzer.analyze_audio('test.wav')
    
    assert results is not None
    assert results['pesq_score'] == 3.5
    assert results['quality_category'] == "Excellent Quality"
    assert results['sample_rate'] == 16000
    assert isinstance(results['snr_db'], float)
    
    # Verify numpy.mean was called
    assert mean_mock.call_count > 0

def test_analyze_audio_sample_rate_conversion(audio_analyzer, mocker):
    """Test audio sample rate conversion to 16kHz"""
    # Create mock audio data with different sample rate
    mock_audio = np.random.random(1000).astype(np.float32)
    
    # Mock soundfile.read to return 44.1kHz audio
    mocker.patch('soundfile.read', return_value=(mock_audio, 44100))
    
    # Mock resampling
    resampled_audio = np.random.random(363).astype(np.float32)  # ~1000 * (16000/44100)
    mocker.patch('scipy.signal.resample', return_value=resampled_audio)
    
    # Mock other dependencies
    mock_magic = mocker.patch('magic.Magic')
    mock_magic.return_value.from_file.return_value = 'audio/x-wav'
    mocker.patch('audio_analyzer.analyzer.pesq', return_value=3.5)
    mocker.patch('numpy.mean', return_value=0.5)
    
    results = audio_analyzer.analyze_audio('test.wav')
    
    assert results is not None
    assert results['sample_rate'] == 16000
    assert results['pesq_score'] == 3.5

def test_analyze_audio_pesq_error(audio_analyzer, mocker):
    """Test handling of PESQ calculation errors"""
    # Mock dependencies
    mock_audio = np.random.random(1000).astype(np.float32)
    mocker.patch('soundfile.read', return_value=(mock_audio, 16000))
    mock_magic = mocker.patch('magic.Magic')
    mock_magic.return_value.from_file.return_value = 'audio/x-wav'
    
    # Mock PESQ to raise an error
    mocker.patch('audio_analyzer.analyzer.pesq', side_effect=ValueError("PESQ calculation failed"))
    
    with pytest.raises(ValueError) as exc_info:
        audio_analyzer.analyze_audio('test.wav')

def test_analyze_audio_zero_signal(audio_analyzer, mocker):
    """Test handling of zero signal power"""
    # Create silent audio (all zeros)
    mock_audio = np.zeros(1000, dtype=np.float32)
    
    # Mock dependencies
    mocker.patch('soundfile.read', return_value=(mock_audio, 16000))
    mock_magic = mocker.patch('magic.Magic')
    mock_magic.return_value.from_file.return_value = 'audio/x-wav'
    mocker.patch('audio_analyzer.analyzer.pesq', return_value=1.0)
    
    # Mock numpy.mean to return 0 for both signal and noise power
    mocker.patch('numpy.mean', return_value=0.0)
    
    results = audio_analyzer.analyze_audio('test.wav')
    
    assert results is not None
    assert results['snr_db'] == 0.0  # Both signal and noise are zero
    assert results['pesq_score'] == 1.0
    assert results['quality_category'] == "Fair Quality"

def test_analyze_audio_no_noise(audio_analyzer, mocker):
    """Test handling of zero noise power"""
    # Create mock audio with signal but no noise
    mock_audio = np.random.random(1000).astype(np.float32)
    
    # Mock dependencies
    mocker.patch('soundfile.read', return_value=(mock_audio, 16000))
    mock_magic = mocker.patch('magic.Magic')
    mock_magic.return_value.from_file.return_value = 'audio/x-wav'
    mocker.patch('audio_analyzer.analyzer.pesq', return_value=4.0)
    
    # Mock numpy.mean to return appropriate values for signal and noise power
    def mock_mean(x, *args, **kwargs):
        if isinstance(x, np.ndarray):
            # Check if this is the noise array (will be all zeros)
            if np.all(x == 0):
                return 0.0  # Noise power
            else:
                return 1.0  # Signal power
        return 0.0
    
    mocker.patch('numpy.mean', side_effect=mock_mean)
    
    # Mock numpy.random.normal to return zeros for noise
    mocker.patch('numpy.random.normal', return_value=np.zeros(1000))
    
    results = audio_analyzer.analyze_audio('test.wav')
    
    assert results is not None
    assert results['snr_db'] == float('inf')  # No noise, finite signal
    assert results['pesq_score'] == 4.0
    assert results['quality_category'] == "Outstanding Quality"