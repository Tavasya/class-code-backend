from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class GrammarCorrection(BaseModel):
    """Model for individual grammar corrections"""
    original_phrase: str
    suggested_correction: str
    explanation: str
    sentence_index: Optional[int] = None
    phrase_index: Optional[int] = None
    sentence_text: Optional[str] = None

class VocabularySuggestion(BaseModel):
    """Model for vocabulary suggestions"""
    original_word: str
    context: str
    advanced_alternatives: List[str]
    level: str
    sentence_index: Optional[int] = None
    phrase_index: Optional[int] = None
    sentence_text: Optional[str] = None

class SentenceAnalysis(BaseModel):
    """Model for sentence-level analysis"""
    original: str
    corrections: Optional[List[GrammarCorrection]] = None
    suggestions: Optional[List[VocabularySuggestion]] = None

class GrammarRequest(BaseModel):
    """Request model for grammar analysis"""
    transcript: str
    question_number: int = 1

class GrammarResponse(BaseModel):
    """Response model for grammar analysis"""
    status: str
    grammar_corrections: Dict[str, Dict[str, Any]]
    vocabulary_suggestions: Dict[str, Dict[str, Any]]
    error: Optional[str] = None
