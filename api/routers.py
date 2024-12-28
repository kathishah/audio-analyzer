"""
API routes for audio analysis
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Union
import tempfile
import os

from audio_analyzer import AudioAnalyzer
from .models import AudioAnalysisResponse, ErrorResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/analyze", 
            response_model=AudioAnalysisResponse,
            responses={
                400: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            })
async def analyze_audio(file: UploadFile = File(...)) -> Dict[str, Union[float, str, int]]:
    """
    Analyze audio file quality
    
    Args:
        file: Uploaded audio file (supports WAV, MP3, WebM, etc.)
        
    Returns:
        Dict containing analysis results:
        - pesq_score: PESQ score (float)
        - quality_category: Quality category (str)
        - snr_db: Signal-to-Noise Ratio in dB (float)
        - sample_rate: Sample rate in Hz (int)
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
    
    # Create temporary file to store upload
    temp_file = None
    try:
        # Save uploaded file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.write(await file.read())
        temp_file.close()
        
        # Analyze audio
        analyzer = AudioAnalyzer()
        results = analyzer.analyze_audio(temp_file.name)
        
        if not results:
            raise HTTPException(
                status_code=500,
                detail="Failed to analyze audio file"
            )
        
        return results
        
    except Exception as e:
        logger.error(f"Error analyzing file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"{str(e)}"
        )
    finally:
        # Cleanup temporary file
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
