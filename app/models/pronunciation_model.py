from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class PronunciationRequest(BaseModel):
    """Request model for pronunciation assessment"""
    audio_file: str
    reference_text: Optional[str] = None

class PronunciationResponse(BaseModel):
    """Response model for pronunciation assessment"""
    status: str
    audio_duration: float
    transcript: str
    overall_pronunciation_score: float
    accuracy_score: float
    fluency_score: float
    prosody_score: float
    completeness_score: float
    critical_errors: List[Dict[str, Any]]
    filler_words: List[Dict[str, Any]]
    word_details: List[Dict[str, Any]]
    improvement_suggestion: str
    error: Optional[str] = None