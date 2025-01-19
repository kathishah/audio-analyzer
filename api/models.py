"""
API models for audio analysis
"""

from datetime import datetime
from typing import Optional, Dict, Union
from ipaddress import ip_address
import uuid

from pydantic import BaseModel, field_validator, IPvAnyAddress, constr, ConfigDict
from sqlalchemy import Column, String, JSON, DateTime, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Custom exceptions
class RecordingSessionError(Exception):
    """Base exception for recording session errors"""
    pass

class InvalidFormatError(RecordingSessionError):
    """Raised when audio format is invalid"""
    pass

# Pydantic models for API
class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None

class StartRecordingSessionRequest(BaseModel):
    device_name: constr(min_length=1, max_length=255)
    ip_address: str
    audio_format: Optional[str] = None
    microphone_details: Optional[str] = None
    speaker_details: Optional[str] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "device_name": "iPhone 12",
            "ip_address": "192.168.1.100",
            "audio_format": "wav",
            "microphone_details": "Built-in Microphone",
            "speaker_details": "Built-in Speaker"
        }
    })

    @field_validator('ip_address')
    def validate_ip_address(cls, v):
        try:
            ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')

class RecordingSessionResponse(BaseModel):
    recording_session_id: uuid.UUID

class AudioAnalysisResponse(BaseModel):
    """Response model for audio analysis results"""
    pesq_score: float
    quality_category: str
    snr_db: float
    sample_rate: int

# SQLAlchemy models for database
class RecordingSession(Base):
    __tablename__ = "recording_sessions"

    recording_session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    device_name = Column(String(255), nullable=False)
    ip_address = Column(String(45), nullable=False)  # IPv6 can be up to 45 chars
    audio_format = Column(String(10), nullable=False)
    microphone_details = Column(String, nullable=True)
    speaker_details = Column(String, nullable=True)
    s3_location = Column(String, nullable=True)
    analysis_output = Column(JSON, nullable=True)
    analysis_score = Column(Numeric(5, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<RecordingSession(id={self.recording_session_id}, device={self.device_name})>"
