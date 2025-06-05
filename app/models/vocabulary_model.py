from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class VocabularySuggestion(BaseModel):
    """Model for vocabulary suggestions"""
    original_word: str
    suggested_word: Optional[str] = None
    original_level: str
    suggested_level: str
    word_type: str
    examples: List[str]
    explanation: Optional[str] = None
    sentence_index: Optional[int] = None
    phrase_index: Optional[int] = None
    sentence_text: Optional[str] = None

class VocabularyFeedback(BaseModel):
    """Model for vocabulary feedback"""
    grade: float
    vocabulary_suggestions: Dict[str, VocabularySuggestion] 