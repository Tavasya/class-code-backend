from fastapi import APIRouter, HTTPException
from app.models.pronunciation_model import PronunciationRequest, PronunciationResponse, WordDetail, PhonemeDetail
from app.services.pronunciation_service import PronunciationService
import logging
import unicodedata

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/analysis", response_model=PronunciationResponse)
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
                error=result.get("error", "Unknown error"),
                question_number=request.question_number
            )
        
        # Process word details to ensure proper Unicode handling
        word_details = []
        for word_data in result.get("word_details", []):
            # Normalize any Unicode strings in the word data
            reference_phonemes = unicodedata.normalize('NFC', word_data.get("reference_phonemes", ""))
            phoneme_details = [
                PhonemeDetail(
                    phoneme=unicodedata.normalize('NFC', p.get("phoneme", "")),
                    accuracy_score=p.get("accuracy_score", 0),
                    error_type=p.get("error_type", "None")
                )
                for p in word_data.get("phoneme_details", [])
            ]
            
            word_details.append(WordDetail(
                word=word_data.get("word", ""),
                offset=word_data.get("offset", 0.0),
                duration=word_data.get("duration", 0.0),
                accuracy_score=word_data.get("accuracy_score", 0),
                error_type=word_data.get("error_type", "None"),
                reference_phonemes=reference_phonemes,
                phoneme_details=phoneme_details
            ))
        
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
            word_details=word_details,
            improvement_suggestion=result.get("improvement_suggestion", ""),
            error=None,
            question_number=request.question_number
        )
        
    except Exception as e:
        logger.exception(f"Error assessing pronunciation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to assess pronunciation: {str(e)}")