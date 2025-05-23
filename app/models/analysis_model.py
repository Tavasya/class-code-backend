from pydantic import BaseModel
from typing import Optional


class AudioDoneMessage(BaseModel):
    """Message model for audio conversion completion"""
    wav_path: str
    question_number: int
    submission_url: str
    original_audio_url: str
    total_questions: Optional[int] = None


class TranscriptionDoneMessage(BaseModel):
    """Message model for transcription completion"""
    text: str
    error: Optional[str] = None
    question_number: int
    submission_url: str
    audio_url: str
    total_questions: Optional[int] = None


class QuestionAnalysisReadyMessage(BaseModel):
    """Message model for when question is ready for analysis"""
    wav_path: str
    transcript: str
    question_number: int
    submission_url: str
    audio_url: str
    total_questions: Optional[int] = 1 