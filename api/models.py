"""
API models for audio analysis
"""

from typing import Optional, Dict, Union
from pydantic import BaseModel, field_validator, IPvAnyAddress, constr, ConfigDict
import uuid
from sqlalchemy import Column, String, JSON, DateTime, Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from db.base import db_setup
import ipaddress

Base = db_setup.Base

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
    audio_format: str

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "device_name": "iPhone 12",
            "ip_address": "192.168.1.100",
            "audio_format": "wav"
        }
    })

    @field_validator('ip_address')
    def validate_ip_address(cls, v):
        try:
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError('Invalid IP address format')

    @field_validator('audio_format')
    def validate_audio_format(cls, v):
        valid_formats = {'wav', 'mp3', 'aac', 'ogg', 'webm'}
        if v.lower() not in valid_formats:
            raise InvalidFormatError(f'Unsupported audio format. Must be one of: {", ".join(valid_formats)}')
        return v.lower()

class UpdateRecordingSessionRequest(BaseModel):
    recording_session_id: uuid.UUID
    microphone_details: Optional[Dict[str, Union[str, int]]] = None
    speaker_details: Optional[Dict[str, Union[str, int]]] = None
    analysis_score: Optional[float] = None
    status: Optional[str] = None
    error_message: Optional[str] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "recording_session_id": "123e4567-e89b-12d3-a456-426614174000",
            "microphone_details": {
                "name": "Built-in Microphone",
                "type": "MEMS",
                "sensitivity": -37
            },
            "speaker_details": {
                "name": "Built-in Speaker",
                "type": "Dynamic",
                "power": 5
            },
            "analysis_score": 0.95,
            "status": "completed",
            "error_message": None
        }
    })

    @field_validator('microphone_details', 'speaker_details')
    def validate_details(cls, v):
        if v is not None:
            required_fields = {'name', 'type'}
            if not all(field in v for field in required_fields):
                raise ValueError(f'Missing required fields: {required_fields}')
        return v

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
