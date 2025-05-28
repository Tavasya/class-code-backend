from fastapi import APIRouter, HTTPException, Request
from app.services.audio_service import AudioService
from app.models.audio_model import AudioConvertRequest, AudioConvertResponse
import base64
import json
import logging
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/audio_proccessing", response_model=AudioConvertResponse)
async def convert_audio(request: Request):
    """Convert a single audio URL to WAV format"""
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

        logger.info(f"Converting audio URL for question {question_number}")

        # Initialize audio service
        audio_service = AudioService()

        # Convert audio to WAV
        result = await audio_service.process_single_audio(audio_url, question_number, submission_url)
        return AudioConvertResponse(**result)

    except Exception as e:
        logger.error(f"Error in audio processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))