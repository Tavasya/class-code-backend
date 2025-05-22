from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.models.transcription_model import TranscriptionResponse
from app.services.transcription_service import TranscriptionService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class TranscribeRequest(BaseModel):
    audio_url: str

@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(request: TranscribeRequest):
    """Transcribe audio from URL"""
    
    try:
        logger.info(f"Processing audio URL: {request.audio_url}")
        
        # Transcribe the audio directly from URL
        result = await TranscriptionService.transcribe_audio_from_url(request.audio_url)
        
        return TranscriptionResponse(
            text=result["text"],
            error=result["error"]
        )
        
    except Exception as e:
        logger.exception(f"Error processing audio URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {str(e)}")
