from fastapi import APIRouter, HTTPException
from app.models.pronunciation_model import PronunciationRequest, PronunciationResponse
from app.services.pronunciation_service import PronunciationService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/pronunciation", response_model=PronunciationResponse)
async def assess_pronunciation(request: PronunciationRequest):
    """Assess pronunciation of audio file with reference text"""
    
    try:
        logger.info(f"Processing pronunciation assessment for: {request.audio_file}")
        
        # Analyze pronunciation using the service
        result = await PronunciationService.analyze_pronunciation(
            request.audio_file,
            request.reference_text
        )
        
        # Check for errors
        if result.get("status") == "error":
            return PronunciationResponse(
                status="error",
                audio_duration=0,
                transcript=result.get("transcript", ""),
                overall_pronunciation_score=0,
                accuracy_score=0,
                fluency_score=0,
                prosody_score=0,
                completeness_score=0,
                critical_errors=[],
                filler_words=[],
                word_details=[],
                improvement_suggestion="",
                error=result.get("error", "Unknown error")
            )
        
        # Return successful response
        return PronunciationResponse(
            status=result.get("status", "success"),
            audio_duration=result.get("audio_duration", 0),
            transcript=result.get("transcript", ""),
            overall_pronunciation_score=result.get("overall_pronunciation_score", 0),
            accuracy_score=result.get("accuracy_score", 0),
            fluency_score=result.get("fluency_score", 0),
            prosody_score=result.get("prosody_score", 0),
            completeness_score=result.get("completeness_score", 0),
            critical_errors=result.get("critical_errors", []),
            filler_words=result.get("filler_words", []),
            word_details=result.get("word_details", []),
            improvement_suggestion=result.get("improvement_suggestion", ""),
            error=None
        )
        
    except Exception as e:
        logger.exception(f"Error assessing pronunciation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to assess pronunciation: {str(e)}")