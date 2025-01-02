"""
API models for audio analysis
"""

from typing import Optional, Dict, Union
from pydantic import BaseModel
import uuid
from sqlalchemy import Column, String, JSON, DateTime, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .database import Base

# Pydantic models for API
class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None

class StartSessionRequest(BaseModel):
    device_name: str
    ip_address: str
    audio_format: str

class UpdateSessionRequest(BaseModel):
    session_id: uuid.UUID
    microphone_details: Dict[str, Union[str, int]]
    speaker_details: Dict[str, Union[str, int]]

class SessionResponse(BaseModel):
    session_id: uuid.UUID

class AudioAnalysisResponse(BaseModel):
    """Response model for audio analysis results"""
    pesq_score: float
    quality_category: str
    snr_db: float
    sample_rate: int

# SQLAlchemy models for database
class RecordingSession(Base):
    __tablename__ = "recording_sessions"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_name = Column(String)
    ip_address = Column(String)
    audio_format = Column(String)
    microphone_details = Column(String, nullable=True)
    speaker_details = Column(String, nullable=True)
    s3_location = Column(String, nullable=True)
    analysis_output = Column(JSON, nullable=True)
    analysis_score = Column(Numeric(precision=5, scale=2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
