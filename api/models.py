"""
API models for audio analysis
"""

from pydantic import BaseModel
from typing import Optional, Dict, Union

class AudioAnalysisResponse(BaseModel):
    """Response model for audio analysis results"""
    pesq_score: float
    quality_category: str
    snr_db: float
    sample_rate: int

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
