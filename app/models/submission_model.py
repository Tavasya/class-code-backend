from pydantic import BaseModel
from typing import List

class SubmissionRequest(BaseModel):
    audio_urls: List[str]
    submission_url: str

class SubmissionResponse(BaseModel):
    status: str
    message: str 