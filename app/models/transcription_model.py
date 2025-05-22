from pydantic import BaseModel
from typing import Optional


class TranscriptionResponse(BaseModel):
    """Response model for transcription"""
    text: str
    error: Optional[str] = None
    question_number: Optional[int] = None