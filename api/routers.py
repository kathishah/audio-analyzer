"""
API routers for audio analysis
"""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, Future
from tempfile import NamedTemporaryFile
from typing import Dict, Union
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse

from db.base import db_setup
from audio_analyzer import AudioAnalyzer
from api.models import (
    AudioAnalysisResponse, 
    ErrorResponse, 
    StartRecordingSessionRequest, 
    RecordingSessionResponse,
    InvalidFormatError,
    RecordingSession
)
from services.db_service import recording_session_crud
from services.s3_service import S3ClientManager, upload_file_to_s3

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

async def _create_local_temp_file(file: UploadFile) -> tuple[str, str]:
    """
    Create a temporary local file from an uploaded file
    
    Args:
        file: The uploaded file
        
    Returns:
        Tuple of (temporary file path, content type)
        
    Raises:
        HTTPException: If file creation fails
    """
    if not file:
        raise HTTPException(status_code=400, detail="No file uploaded")
        
    try:
        temp_file = NamedTemporaryFile(delete=False)
        temp_file.write(await file.read())
        temp_file.close()
        return temp_file.name, file.content_type
    except Exception as e:
        logger.error(f"Failed to create temporary file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process uploaded file"
        )

def _upload_to_s3_background(src_file_path: str, content_type: str) -> Future:
    """
    Upload a file to S3 in the background
    
    Args:
        src_file_path: Path to source file
        content_type: File content type
        
    Returns:
        Future: Future that resolves to the S3 URL when upload completes
    """
    def upload() -> str:
        try:
            logger.info(f"Uploading file to S3 in background from {src_file_path}")
            s3_url = upload_file_to_s3(src_file_path, content_type, max_retries=2)
            logger.info(f"File uploaded to S3: {s3_url}")
            return s3_url
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            raise
            
    return executor.submit(upload)

async def _analyze_audio_file(src_file_path: str) -> Dict[str, Union[float, str, int]]:
    """
    Analyze an audio file and return results
    
    Args:
        src_file_path: Path to the audio file
        
    Returns:
        Dict containing analysis results
        
    Raises:
        HTTPException: If analysis fails
    """
    try:
        analyzer = AudioAnalyzer()
        results = analyzer.analyze_audio(src_file_path)
        
        if not results:
            raise HTTPException(
                status_code=500,
                detail="Failed to analyze audio file"
            )
            
        return results
            
    except Exception as e:
        logger.error(f"Failed to analyze audio file: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to analyze audio file"
        )

@router.post("/analyze", 
            response_model=AudioAnalysisResponse,
            responses={
                400: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            })
async def analyze_audio(
    file: UploadFile = File(...),
) -> Dict[str, Union[float, str, int]]:
    """
    Analyze audio file quality without storing the file
    
    Args:
        file: Uploaded audio file (supports WAV, MP3, WebM, etc.)
        
    Returns:
        Dict containing analysis results:
        - pesq_score: PESQ score (float)
        - quality_category: Quality category (str)
        - snr_db: Signal-to-Noise Ratio in dB (float)
        - sample_rate: Sample rate in Hz (int)
    """
    temp_file_path = None
    try:
        # Create temporary local file
        temp_file_path, _ = await _create_local_temp_file(file)
        
        # Analyze audio
        return await _analyze_audio_file(temp_file_path)
                
    except Exception as e:
        logger.error(f"Error analyzing audio: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing audio: {str(e)}"
        )
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@router.post("/recording-session/{recording_session_id}/analyze", 
            response_model=AudioAnalysisResponse,
            responses={
                400: {"model": ErrorResponse},
                404: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            })
async def analyze_session_audio(
    recording_session_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
) -> Dict[str, Union[float, str, int]]:
    """
    Analyze audio file quality for a specific recording session
    
    Args:
        recording_session_id: ID of the recording session to analyze audio for
        file: Uploaded audio file (supports WAV, MP3, WebM, etc.)
        db: Database session
        
    Returns:
        Dict containing analysis results:
        - pesq_score: PESQ score (float)
        - quality_category: Quality category (str)
        - snr_db: Signal-to-Noise Ratio in dB (float)
        - sample_rate: Sample rate in Hz (int)
        
    Raises:
        HTTPException:
            - 400: If no file uploaded or invalid file format
            - 404: If recording session not found
            - 500: For analysis or server errors
    """
    try:
        # Verify session exists
        session = recording_session_crud.get_session(db, recording_session_id)
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Recording session {recording_session_id} not found"
            )
            
        temp_file_path = None
        try:
            # Create temporary local file
            temp_file_path, content_type = await _create_local_temp_file(file)
            
            # Start S3 upload in background and get future
            s3_future = _upload_to_s3_background(temp_file_path, content_type)

            # Analyze audio
            results = await _analyze_audio_file(temp_file_path)
                
            # Get S3 URL from future and update session
            try:
                s3_url = s3_future.result(timeout=30)  # Wait up to 30 seconds for upload
                session.analysis_output = results
                session.s3_location = s3_url
                session.analysis_score = results.get('pesq_score')  # Store PESQ score separately
                recording_session_crud.update(db, model_obj=session)
            except Exception as e:
                logger.error(f"Failed to get S3 URL: {str(e)}")
                # Still return results even if S3 upload failed
                session.analysis_output = results
                session.analysis_score = results.get('pesq_score')
                recording_session_crud.update(db, model_obj=session)
            
            return results
            
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logger.error(f"Error analyzing audio: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing audio: {str(e)}"
        )


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
    logger.info("Starting new recording session with request: %s", request)
    try:
        # Create SQLAlchemy model instance from Pydantic model
        db_model = RecordingSession(
            device_name=request.device_name,
            ip_address=request.ip_address,
            audio_format=request.audio_format
        )
        db_obj = recording_session_crud.create(db, model_obj=db_model)
        logger.info(f"Created new recording session: {db_obj.recording_session_id}")
        return RecordingSessionResponse(recording_session_id=db_obj.recording_session_id)
        
    except IntegrityError as e:
        logger.warning(f"Integrity error: {str(e)}")
        raise HTTPException(
            status_code=409,
            detail="Conflict occurred while creating recording session",
            headers={"X-Error-Code": "CONFLICT"}
        )
        
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
        logger.error(f"Failed to create recording session: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error occurred while creating recording session",
            headers={"X-Error-Code": "INTERNAL_ERROR"}
        )


@router.get("/recording-session/{id}")
async def get_recording_session(
    id: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get details of a specific recording session by ID
    
    Args:
        id: The ID of the recording session to retrieve
        db: Database session (injected by FastAPI)
        
    Returns:
        dict: Dictionary containing all session details including analysis results
        
    Raises:
        HTTPException: 
            - 404: If recording session not found or invalid ID format
            - 500: For server errors
    """
    try:
        try:
            session = recording_session_crud.get_session(db, id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=404,
                detail=f"Invalid recording session ID: {id}"
            )
            
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Recording session with id {id} not found"
            )
        session_dict = session.__dict__
        session_dict.pop('_sa_instance_state', None)  # Remove SQLAlchemy internal state
        return session_dict
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving recording session {id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving recording session: {str(e)}"
        )


@router.get("/s3-token/status", 
          responses={
              200: {"model": dict},
              500: {"model": ErrorResponse}
          })
async def get_s3_token_status() -> Dict:
    """
    Get the current S3 token status.
    
    Returns:
        dict: Token status containing:
            - status: 'active' or 'expired'
            - expires_in_seconds: seconds until expiration (if active)
            - expiry_time: ISO formatted expiry time (if active)
    """
    if not S3ClientManager.is_initialized():
        raise HTTPException(
            status_code=500,
            detail="S3 client is not initialized. Check if required environment variables are set.",
            headers={"X-Error-Code": "S3_CLIENT_NOT_INITIALIZED"}
        )
        
    try:
        s3_manager = S3ClientManager.get_instance()
        return s3_manager.get_token_status()
    except Exception as e:
        logger.error(f"Failed to get token status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get token status: {str(e)}",
            headers={"X-Error-Code": "TOKEN_STATUS_ERROR"}
        )


@router.post("/s3-token/refresh",
           responses={
               200: {"model": dict},
               500: {"model": ErrorResponse}
           })
async def refresh_s3_token() -> Dict:
    """
    Force a refresh of the S3 token.
    
    Returns:
        dict: New token status
    """
    if not S3ClientManager.is_initialized():
        raise HTTPException(
            status_code=500,
            detail="S3 client is not initialized. Check if required environment variables are set.",
            headers={"X-Error-Code": "S3_CLIENT_NOT_INITIALIZED"}
        )
        
    try:
        s3_manager = S3ClientManager.get_instance()
        return s3_manager.force_refresh_token()
    except Exception as e:
        logger.error(f"Failed to refresh token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh token: {str(e)}",
            headers={"X-Error-Code": "TOKEN_REFRESH_ERROR"}
        )


@router.post("/s3-token/expire",
           responses={
               200: {"model": dict},
               500: {"model": ErrorResponse}
           })
async def expire_s3_token() -> Dict:
    """
    Force the current S3 token to expire.
    
    Returns:
        dict: Token status after expiration
    """
    if not S3ClientManager.is_initialized():
        raise HTTPException(
            status_code=500,
            detail="S3 client is not initialized. Check if required environment variables are set.",
            headers={"X-Error-Code": "S3_CLIENT_NOT_INITIALIZED"}
        )
        
    try:
        s3_manager = S3ClientManager.get_instance()
        return s3_manager.force_token_expiration()
    except Exception as e:
        logger.error(f"Failed to expire token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to expire token: {str(e)}",
            headers={"X-Error-Code": "TOKEN_EXPIRE_ERROR"}
        )
