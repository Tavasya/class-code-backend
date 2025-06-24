from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Version 3: Collocation-based vocabulary model with categorization
class VocabularySuggestion(BaseModel):
    """Model for vocabulary collocation suggestions"""
    type: str = "vocabulary"
    category: int  # 1-10 category number for vocabulary issues
    original_word: str
    suggested_word: str
    explanation: str
    examples: List[str]
    sentence_index: Optional[int] = None
    phrase_index: Optional[int] = None
    sentence_text: Optional[str] = None

# Legacy CEFR-based model (v2) - commented out but preserved
# class VocabularySuggestionLegacy(BaseModel):
#     """Model for CEFR-based vocabulary suggestions"""
#     original_word: str
#     suggested_word: Optional[str] = None
#     original_level: str
#     suggested_level: str
#     word_type: str
#     examples: List[str]
#     explanation: Optional[str] = None
#     sentence_index: Optional[int] = None
#     phrase_index: Optional[int] = None
#     sentence_text: Optional[str] = None

class VocabularyFeedback(BaseModel):
    """Model for vocabulary feedback"""
    grade: float
    vocabulary_suggestions: Dict[str, VocabularySuggestion] 