"""
Core audio analysis functionality
"""

import logging
import soundfile as sf
import numpy as np
from pesq import pesq
from scipy import signal
import magic
from pydub import AudioSegment
from typing import Dict, Union, Optional
import os

from .utils import get_media_info, cleanup_temp_file, create_temp_wav

logger = logging.getLogger(__name__)

class AudioAnalyzer:
    """Class for analyzing audio quality using PESQ metric"""
    
    @staticmethod
    def categorize_pesq(pesq_score: float) -> str:
        """
        Categorize PESQ score into quality levels
        
        Args:
            pesq_score (float): PESQ score (ranges from -0.5 to 4.5)
        
        Returns:
            str: Quality category
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

    def convert_to_wav(self, input_file: str) -> str:
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
            temp_wav_path = create_temp_wav()
            
            # Convert to WAV using the detected format
            format_map = {
                'audio/webm': 'webm',
                'video/webm': 'webm',
                'audio/mpeg': 'mp3',
                'audio/ogg': 'ogg',
                'audio/x-m4a': 'm4a',
                'audio/aac': 'aac',
                'audio/flac': 'flac',
                'video/mp4': 'mp4',
                'video/x-m4v': 'm4v'
            }
            
            detected_format = format_map.get(file_type, file_type.split('/')[-1])
            logger.info(f"Using format '{detected_format}' for conversion")
            
            audio = AudioSegment.from_file(input_file, format=detected_format)
            audio.export(temp_wav_path, format="wav")
            logger.info(f"Converted {detected_format} to WAV: {temp_wav_path}")
            return temp_wav_path
            
        except Exception as e:
            logger.error(f"Error converting file: {str(e)}")
            if 'temp_wav_path' in locals():
                cleanup_temp_file(temp_wav_path)
            raise

    def analyze_audio(self, input_file: str) -> Optional[Dict[str, Union[float, str, int]]]:
        """
        Analyze audio quality using PESQ metric
        
        Args:
            input_file (str): Path to the input audio file
            
        Returns:
            Optional[Dict[str, Union[float, str, int]]]: Analysis results or None if error
        """
        wav_file = None
        try:
            logger.info(f"Starting analysis of file: {os.path.basename(input_file)}")
            
            # Convert to WAV if necessary
            wav_file = self.convert_to_wav(input_file)
            
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
            
            # Create degraded version for comparison
            logger.info("Creating degraded version of audio for comparison...")
            noise = np.random.normal(0, 0.01, len(audio))
            degraded_audio = audio + noise
            
            # Calculate PESQ score
            logger.info("Calculating PESQ score...")
            pesq_score = pesq(sample_rate, audio, degraded_audio, 'nb')
            logger.info(f"PESQ score calculated: {pesq_score:.2f}")
            
            # Calculate SNR
            logger.info("Calculating Signal-to-Noise Ratio...")
            noise_power = np.mean(noise ** 2)
            signal_power = np.mean(audio ** 2)
            snr = 10 * np.log10(signal_power / noise_power)
            logger.info(f"SNR calculated: {snr:.2f} dB")
            
            results = {
                'pesq_score': round(pesq_score, 2),
                'quality_category': self.categorize_pesq(pesq_score),
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
            if wav_file and wav_file != input_file:
                cleanup_temp_file(wav_file)