from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.models.transcription_model import TranscriptionResponse
from app.services.transcription_service import TranscriptionService
import base64
import json
import logging
from typing import List

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/audio_proccessing", response_model=TranscriptionResponse)
async def transcribe_audio(request: Request):
    """Transcribe a single audio URL"""
    try:
        body = await request.json()
        # Check if this is a Pub/Sub push message
        if "message" in body and "data" in body["message"]:
            # Decode base64 data
            decoded_data = base64.b64decode(body["message"]["data"]).decode("utf-8")
            data = json.loads(decoded_data)
            audio_url = data["audio_url"]  # Single audio URL
            question_number = data["question_number"]
            submission_url = data.get("submission_url")
        else:
            # Assume it's a direct request
            data = body
            audio_url = data["audio_url"]
            question_number = data["question_number"]
            submission_url = data.get("submission_url")

        logger.info(f"Transcribing audio URL for question {question_number}")

        # Initialize transcription service
        transcription_service = TranscriptionService()

        # Transcribe the audio
        result = await transcription_service.process_single_transcription(audio_url, question_number, submission_url)
        return TranscriptionResponse(**result)
        
    except Exception as e:
        logger.exception(f"Error processing audio URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {str(e)}")
