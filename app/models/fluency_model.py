from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class WordDetail(BaseModel):
    """Model for individual word details in speech"""
    word: str
    offset: float
    duration: float
    accuracy_score: float
    error_type: str

class FluencyRequest(BaseModel):
    """Request model for fluency assessment"""
    reference_text: str
    word_details: Optional[List[WordDetail]] = None
    audio_duration: Optional[float] = None # Total duration of the audio in seconds

class FluencyMetrics(BaseModel):
    """Fluency metrics model"""
    speech_rate: float
    hesitation_ratio: float
    pause_pattern_score: float
    overall_fluency_score: float
    words_per_minute: float

class CoherenceMetrics(BaseModel):
    """Coherence metrics model"""
    topic_consistency: float
    logical_flow: float
    idea_development: float
    overall_coherence_score: float

class FluencyResponse(BaseModel):
    """Response model for fluency assessment"""
    status: str
    fluency_metrics: FluencyMetrics
    coherence_metrics: CoherenceMetrics
    key_findings: List[str]
    improvement_suggestions: List[str]
    error: Optional[str] = None

class SimpleFluencyResponse(BaseModel):
    """Simplified response model for the fluency endpoint"""
    grade: float
    issues: List[str]
    wpm: float
    status: str = "success" # Optional: include a status if desired
    error: Optional[str] = None # Optional: include error if an error occurs before this transformation