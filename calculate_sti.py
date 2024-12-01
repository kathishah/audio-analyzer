import soundfile as sf
import numpy as np
from pesq import pesq
from scipy import signal
import argparse
import logging
import os
from pydub import AudioSegment
import tempfile
import magic
import json
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def categorize_pesq(pesq_score):
    """
    Categorize PESQ score into quality levels
    
    Parameters:
    -----------
    pesq_score : float
        PESQ score (ranges from -0.5 to 4.5)
    
    Returns:
    --------
    str
        Quality category
    """
    if pesq_score < 1:
        return "Poor Quality"
    elif 1 <= pesq_score < 2:
        return "Fair Quality"
    elif 2 <= pesq_score < 3:
        return "Good Quality"
    elif 3 <= pesq_score < 4:
        return "Excellent Quality"
    else:
        return "Outstanding Quality"

def get_media_info(file_path):
    """
    Get media information using ffprobe
    
    Args:
        file_path (str): Path to the media file
        
    Returns:
        dict: Dictionary containing media information
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return None
    except Exception as e:
        logger.error(f"Error getting media info: {str(e)}")
        return None

def convert_to_wav(input_file):
    """
    Convert non-WAV audio files to WAV format if necessary
    
    Args:
        input_file (str): Path to the input audio file
        
    Returns:
        str: Path to WAV file (either converted or original)
    """
    # Get MIME type of the file
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(input_file)
    logger.info(f"Detected file type: {file_type}")
    
    # Check if file is already a WAV file
    if file_type == 'audio/x-wav':
        return input_file
    
    # For WebM files, check actual content
    if file_type == 'video/webm':
        media_info = get_media_info(input_file)
        if media_info and 'streams' in media_info:
            # Check if file has video streams
            has_video = any(stream['codec_type'] == 'video' 
                          for stream in media_info['streams'])
            if not has_video:
                logger.info("WebM file contains only audio streams")
                file_type = 'audio/webm'
    
    # Check if file is an audio file or video file with audio
    if not (file_type.startswith('audio/') or file_type == 'video/webm'):
        raise ValueError(f"File is not an audio file or video with audio. Detected type: {file_type}")
    
    try:
        logger.info(f"Converting {file_type} file to WAV format...")
        # Create a temporary file with .wav extension
        temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()
        
        # Convert to WAV using the detected format
        format_map = {
            'audio/webm': 'webm',
            'video/webm': 'webm',  # Handle video/webm as webm format
            'audio/mpeg': 'mp3',
            'audio/ogg': 'ogg',
            'audio/x-m4a': 'm4a',
            'audio/aac': 'aac',
            'audio/flac': 'flac',
            'video/mp4': 'mp4',    # Add support for other video formats
            'video/x-m4v': 'm4v'
        }
        
        detected_format = format_map.get(file_type, file_type.split('/')[-1])
        logger.info(f"Using format '{detected_format}' for conversion")
        
        # Load audio from file (pydub will extract audio from video if necessary)
        audio = AudioSegment.from_file(input_file, format=detected_format)
        audio.export(temp_wav_path, format="wav")
        logger.info(f"Converted {detected_format} to WAV: {temp_wav_path}")
        return temp_wav_path
        
    except Exception as e:
        logger.error(f"Error converting file: {str(e)}")
        if os.path.exists(temp_wav_path):
            cleanup_temp_file(temp_wav_path)
        raise

def cleanup_temp_file(file_path):
    """
    Clean up temporary WAV file if it exists
    """
    if os.path.exists(file_path) and file_path.endswith('.wav'):
        try:
            os.unlink(file_path)
            logger.info("Cleaned up temporary WAV file")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file: {str(e)}")

def analyze_speech_quality(input_file):
    """
    Analyze speech quality using PESQ metric for a given audio file.
    
    Args:
        input_file (str): Path to the input audio file (WebM or WAV)
        
    Returns:
        dict: Dictionary containing quality metrics
    """
    wav_file = None
    try:
        logger.info(f"Starting analysis of file: {os.path.basename(input_file)}")
        
        # Convert to WAV if necessary
        wav_file = convert_to_wav(input_file)
        
        # Read the audio file
        logger.info("Reading audio file...")
        audio, sample_rate = sf.read(wav_file)
        logger.info(f"Audio file loaded successfully. Sample rate: {sample_rate} Hz")
        
        # If stereo, convert to mono by taking the mean of both channels
        if len(audio.shape) > 1:
            logger.info("Converting stereo to mono...")
            audio = np.mean(audio, axis=1)
            logger.info("Stereo to mono conversion complete")
        
        # Ensure the audio is in the correct format (float between -1 and 1)
        logger.info("Normalizing audio data...")
        audio = audio.astype(np.float32)
        
        # Resample to 16kHz if necessary (PESQ requirement)
        if sample_rate != 16000:
            logger.info(f"Resampling audio from {sample_rate}Hz to 16000Hz...")
            number_of_samples = round(len(audio) * float(16000) / sample_rate)
            audio = signal.resample(audio, number_of_samples)
            sample_rate = 16000
            logger.info("Resampling complete")
        
        # For demonstration, we'll create a slightly degraded version of the signal
        logger.info("Creating degraded version of audio for comparison...")
        noise = np.random.normal(0, 0.01, len(audio))
        degraded_audio = audio + noise
        
        # Calculate PESQ score
        logger.info("Calculating PESQ score...")
        pesq_score = pesq(sample_rate, audio, degraded_audio, 'nb')
        logger.info(f"PESQ score calculated: {pesq_score:.2f}")
        
        # Calculate signal-to-noise ratio (SNR)
        logger.info("Calculating Signal-to-Noise Ratio...")
        noise_power = np.mean(noise ** 2)
        signal_power = np.mean(audio ** 2)
        snr = 10 * np.log10(signal_power / noise_power)
        logger.info(f"SNR calculated: {snr:.2f} dB")
        
        results = {
            'pesq_score': round(pesq_score, 2),
            'quality_category': categorize_pesq(pesq_score),
            'snr_db': round(snr, 2),
            'sample_rate': sample_rate
        }
        
        logger.info("Analysis completed successfully")
        return results

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return None
    finally:
        # Clean up temporary WAV file if it was created
        if wav_file != input_file:
            cleanup_temp_file(wav_file)

def main():
    parser = argparse.ArgumentParser(description='Analyze speech quality using PESQ metric')
    parser.add_argument('input_file', type=str, help='Path to the input audio file (WebM or WAV)')
    parser.add_argument('--log-file', type=str, help='Path to log file (optional)')
    args = parser.parse_args()
    
    # Add file handler if log file is specified
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    
    logger.info("Starting speech quality analysis")
    results = analyze_speech_quality(args.input_file)
    
    if results:
        print("\nSpeech Quality Analysis Results:")
        print("-" * 30)
        for key, value in results.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        logger.info("Analysis results displayed successfully")
    else:
        logger.error("Analysis failed to produce results")

if __name__ == "__main__":
    main()