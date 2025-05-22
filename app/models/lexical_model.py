from pydantic import BaseModel
from typing import List, Optional

class LexicalCorrection(BaseModel):
    original_phrase: str
    suggested_phrase: str
    explanation: str
    resource_type: str  # collocation, idiom, or word_usage

class LexicalFeedback(BaseModel):
    sentence: str
    corrections: List[LexicalCorrection]

class LexicalAnalysisResponse(BaseModel):
    lexical_feedback: List[LexicalFeedback]
    error: Optional[str] = None 