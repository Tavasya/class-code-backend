from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class FluencyRequest(BaseModel):
    """Request model for fluency assessment"""
    reference_text: str

class FluencyResponse(BaseModel):
    """Response model for fluency assessment"""
    status: str
    overall_fluency_score: float
    completeness_score: float
    critical_errors: List[Dict[str, Any]]
    filler_words: List[Dict[str, Any]]
    word_details: List[Dict[str, Any]]
    improvement_suggestion: str
    error: Optional[str] = None