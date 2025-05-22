from pydantic import BaseModel
from typing import Optional

class TranscriptionResponse(BaseModel):
    """Basic transcription response"""
    text: str
    error: Optional[str] = None
    question_number: int = 1