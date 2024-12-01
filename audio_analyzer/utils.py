"""
Utility functions for audio analysis
"""

import logging
import subprocess
import json
import os
import tempfile
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

def get_media_info(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Get media information using ffprobe
    
    Args:
        file_path (str): Path to the media file
        
    Returns:
        Optional[Dict[str, Any]]: Dictionary containing media information or None if error
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

def cleanup_temp_file(file_path: str) -> None:
    """
    Clean up temporary WAV file if it exists
    
    Args:
        file_path (str): Path to the temporary file
    """
    if os.path.exists(file_path) and file_path.endswith('.wav'):
        try:
            os.unlink(file_path)
            logger.info("Cleaned up temporary WAV file")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary file: {str(e)}")

def create_temp_wav() -> str:
    """
    Create a temporary WAV file
    
    Returns:
        str: Path to the temporary WAV file
    """
    temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
    temp_wav_path = temp_wav.name
    temp_wav.close()
    return temp_wav_path