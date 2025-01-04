"""
API routes for audio analysis
"""

import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import Dict, Union
import tempfile
import os
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from audio_analyzer import AudioAnalyzer
from .models import (
    AudioAnalysisResponse, 
    ErrorResponse, 
    StartRecordingSessionRequest, 
    RecordingSessionResponse,
    RecordingSessionError,
    InvalidFormatError
)
from services.s3_service import upload_file_to_s3
from services.db_service import recording_session_crud
from db.base import db_setup

logger = logging.getLogger(__name__)

router = APIRouter()

# ThreadPoolExecutor for async background tasks
executor = ThreadPoolExecutor(max_workers=2)

# Dependency to get database session
def get_db():
    db = next(db_setup.get_session())
    try:
        yield db
    finally:
        db.close()

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
    try:
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
            
        except InvalidFormatError as e:
            logger.warning(f"Invalid audio format: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=str(e),
                headers={"X-Error-Code": "INVALID_FORMAT"}
            )
            
        except ValueError as e:
            logger.warning(f"Invalid request data: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=str(e),
                headers={"X-Error-Code": "INVALID_DATA"}
            )
            
        except Exception as e:
            logger.error(f"Error analyzing file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Internal server error occurred while analyzing audio file",
                headers={"X-Error-Code": "INTERNAL_ERROR"}
            )
        
    finally:
        # Cleanup temporary file
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


@router.post("/recording-session/start",
            response_model=RecordingSessionResponse,
            responses={
                400: {"model": ErrorResponse},
                409: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            })
async def start_recording_session(
    request: StartRecordingSessionRequest,
    db: Session = Depends(get_db)
) -> RecordingSessionResponse:
    """
    Start a new recording session and get a recording session ID
    
    Args:
        request: Recording session details including device name, IP address, and audio format
        db: Database session (injected by FastAPI)
    
    Returns:
        RecordingSessionResponse with the new recording session ID
    
    Raises:
        HTTPException: 
            - 400: If request data is invalid
            - 409: If a conflict occurs (e.g., duplicate session)
            - 500: For other server errors
    """
    try:
        db_obj = recording_session_crud.create(db, obj_in=request)
        logger.info(f"Created new recording session: {db_obj.recording_session_id}")
        return RecordingSessionResponse(recording_session_id=db_obj.recording_session_id)
        
    except InvalidFormatError as e:
        logger.warning(f"Invalid audio format: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
            headers={"X-Error-Code": "INVALID_FORMAT"}
        )
        
    except ValueError as e:
        logger.warning(f"Invalid request data: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
            headers={"X-Error-Code": "INVALID_DATA"}
        )
        
    except IntegrityError as e:
        logger.error(f"Database integrity error: {str(e)}")
        raise HTTPException(
            status_code=409,
            detail="A recording session with these details already exists",
            headers={"X-Error-Code": "DUPLICATE_SESSION"}
        )
        
    except Exception as e:
        logger.error(f"Failed to create recording session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error occurred while creating recording session",
            headers={"X-Error-Code": "INTERNAL_ERROR"}
        )
