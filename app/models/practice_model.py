from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class PracticePronunciationRequest(BaseModel):
    """Request model for practice pronunciation analysis"""
    audio_url: str
    transcript: str
    user_id: Optional[str] = None  # Optional for tracking
    webhook_url: Optional[str] = None  # URL to send results to (required for async processing)


class PracticePronunciationResponse(BaseModel):
    """Response model for practice pronunciation analysis"""
    overall_pronunciation_score: float
    accuracy_score: float
    fluency_score: float
    prosody_score: float
    completeness_score: float
    word_details: List[Dict[str, Any]]
    critical_errors: List[Dict[str, Any]]
    improvement_suggestions: str
    processing_time_ms: int
    audio_duration_seconds: float
    transcript_used: str


class PracticeSubmissionResponse(BaseModel):
    """Response model for practice pronunciation submission (async)"""
    request_id: str
    status: str
    message: str
    estimated_processing_time_seconds: str


class PracticeStatusResponse(BaseModel):
    """Response model for practice pronunciation status check"""
    request_id: str
    status: str  # "pending", "processing", "completed", "failed"
    result: Optional[PracticePronunciationResponse] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None


class PracticeErrorResponse(BaseModel):
    """Error response model for practice endpoints"""
    error: str
    detail: str
    processing_time_ms: int 