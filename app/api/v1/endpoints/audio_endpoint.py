from fastapi import APIRouter, HTTPException
from app.services.audio_service import AudioService
from app.models.audio_model import AudioConvertRequest, AudioConvertResponse

router = APIRouter()

@router.post("/audio_proccessing", response_model=AudioConvertResponse)
async def convert_audio(request: AudioConvertRequest):
    """Download audio from Supabase and convert to WAV for speech analysis"""
    try:
        audio_service = AudioService()
        wav_path = await audio_service.convert_to_wav(request.url)
        
        return AudioConvertResponse(
            wav_path=wav_path,
            question_number=request.question_number
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))