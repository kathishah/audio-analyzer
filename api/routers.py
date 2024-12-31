"""
API routes for audio analysis
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Union
import tempfile
import os
from concurrent.futures import ThreadPoolExecutor

from audio_analyzer import AudioAnalyzer
from .models import AudioAnalysisResponse, ErrorResponse
from services.s3_service import upload_file_to_s3

logger = logging.getLogger(__name__)

router = APIRouter()

# ThreadPoolExecutor for async background tasks
executor = ThreadPoolExecutor(max_workers=2)

def save_to_s3_in_background(temp_file_path: str, content_type: str):
    """
    Save file to S3 in the background.

    Args:
        temp_file_path: Path to the temporary file.
        content_type: MIME type of the file.
    """
    try:
        s3_url = upload_file_to_s3(temp_file_path, content_type)
        logger.info(f"File uploaded to S3: {s3_url}")
    except Exception as e:
        logger.error(f"Failed to upload file to S3: {str(e)}")



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
        
        # Submit S3 upload task to the thread pool
        logger.info(f"Submitting file to S3 in background: {temp_file.name}")
        executor.submit(save_to_s3_in_background, temp_file.name, file.content_type)

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
