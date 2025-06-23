from pydantic import BaseModel
from typing import Optional, Dict, Any


class ParagraphRestructuringRequest(BaseModel):
    """Request model for paragraph restructuring"""
    transcript: str
    current_band: Optional[str] = None  # If not provided, will be auto-detected
    submission_url: Optional[str] = None  # For testing endpoint


class ParagraphRestructuringResult(BaseModel):
    """Result model for paragraph restructuring"""
    original_band: str
    target_band: str
    improved_transcript: str


class ParagraphRestructuringResponse(BaseModel):
    """Response model for paragraph restructuring"""
    result: Optional[ParagraphRestructuringResult] = None
    status: str
    error: Optional[str] = None


class BandLevelDetectionResult(BaseModel):
    """Model for band level detection results"""
    detected_band: str
    confidence_score: float
    score_breakdown: Dict[str, Any] 