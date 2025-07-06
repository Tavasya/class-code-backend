from pydantic import BaseModel

class ImproveTranscriptResponse(BaseModel):
    """Response model for improve transcript endpoint"""
    success: bool
    message: str
    session_id: str
    status: str