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
import tempfile

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

        # Create a temporary file path for the WAV conversion
        temp_wav_path = create_temp_wav()
        
        try:
            logger.info(f"Converting {file_type} file to WAV format...")
                        
            audio = AudioSegment.from_file(input_file)
            audio.export(temp_wav_path, format="wav")
            logger.info(f"Converted {file_type} to WAV: {temp_wav_path}")
            return temp_wav_path
            
        except Exception as e:
            logger.error(f"Error converting file: {str(e)}")
            if os.path.exists(temp_wav_path):
                cleanup_temp_file(temp_wav_path)
            raise e

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
            
            # Handle division by zero for SNR calculation
            if noise_power == 0:
                if signal_power == 0:
                    snr = 0.0  # Both signal and noise are zero
                else:
                    snr = float('inf')  # No noise, finite signal
            else:
                snr = 10 * np.log10(signal_power / noise_power)
            
            logger.info(f"SNR calculated: {snr:.2f} dB")
            
            results = {
                'pesq_score': round(pesq_score, 2),
                'quality_category': self.categorize_pesq(pesq_score),
                'snr_db': float('inf') if np.isinf(snr) else round(snr, 2),
                'sample_rate': sample_rate
            }
            
            logger.info("Analysis completed successfully")
            return results

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            raise e
        finally:
            # Clean up temporary WAV file if it was created
            if wav_file and wav_file != input_file:
                cleanup_temp_file(wav_file)