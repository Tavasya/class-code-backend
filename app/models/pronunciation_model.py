from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class PronunciationRequest(BaseModel):
    """Request model for pronunciation assessment"""
    audio_file: str
    reference_text: Optional[str] = None
    question_number: int = 1

class PhonemeDetail(BaseModel):
    """Model for phoneme details with proper Unicode handling"""
    phoneme: str = Field(description="IPA phoneme with accent marks")
    accuracy_score: float = 0
    error_type: str = "None"

class WordDetail(BaseModel):
    """Model for word-level pronunciation details"""
    word: str
    offset: float
    duration: float
    accuracy_score: float
    error_type: str
    reference_phonemes: str = Field(description="IPA string with accent marks")
    phoneme_details: List[PhonemeDetail]

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
    word_details: List[WordDetail]  # Now using the WordDetail model with proper phoneme handling
    improvement_suggestion: str
    error: Optional[str] = None
    question_number: int = 1

    class Config:
        """Configure Pydantic model to handle Unicode properly"""
        json_encoders = {
            str: lambda v: v  # Preserve Unicode characters as is
        }