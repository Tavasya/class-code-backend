from typing import List
from pydantic import BaseModel

class VocabularySuggestion(BaseModel):
    """
    Model for vocabulary enhancement suggestions.
    """
    original_word: str  # The original word from the transcript
    context: str  # The full sentence containing the word
    advanced_alternatives: List[str]  # List of suggested alternative words
    level: str  # Target CEFR level (e.g., "B1", "B2", "C1")
    sentence_index: int  # Index of the sentence in the transcript
    phrase_index: int  # Index of the word within the sentence 