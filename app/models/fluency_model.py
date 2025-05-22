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

class FluencyMetrics(BaseModel):
    """Fluency metrics model"""
    speech_rate: float
    hesitation_ratio: float
    pause_pattern_score: float
    overall_fluency_score: float

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