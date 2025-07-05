from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
import time
import uuid
from app.models.practice_model import (
    PracticePronunciationRequest, 
    PracticePronunciationResponse, 
    PracticeSubmissionResponse,
    PracticeStatusResponse,
    PracticeErrorResponse
)
from app.pubsub.client import PubSubClient
from app.core.results_store import ResultsStore
from app.services.audio_service import AudioService
from app.services.pronunciation_service import PronunciationService
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize pub/sub client and results store
pubsub_client = PubSubClient()
results_store = ResultsStore()

@router.post("/analyze-pronunciation", response_model=PracticeSubmissionResponse)
async def analyze_pronunciation(request: PracticePronunciationRequest):
    """
    Submit practice pronunciation analysis request.
    
    This endpoint accepts the audio URL and transcript, submits it to the 
    processing queue, and returns a request ID. Results will be delivered 
    via webhook when processing is complete.
    """
    try:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        logger.info(f"🎤 Submitting practice pronunciation request: {request_id}")
        logger.info(f"👤 User: {request.user_id}")
        logger.info(f"🔗 Audio URL: {request.audio_url}")
        logger.info(f"📝 Transcript length: {len(request.transcript)} characters")
        
        # Validate inputs
        if not request.audio_url or not request.audio_url.strip():
            raise HTTPException(
                status_code=400, 
                detail="Audio URL cannot be empty"
            )
            
        if not request.transcript or not request.transcript.strip():
            raise HTTPException(
                status_code=400, 
                detail="Transcript cannot be empty"
            )
        
        # Validate URL format (basic check)
        if not request.audio_url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400, 
                detail="Audio URL must be a valid HTTP/HTTPS URL"
            )
            
        # webhook_url is optional - if not provided, user can poll for status
        
        # Prepare message for pub/sub
        message_data = {
            "request_id": request_id,
            "audio_url": request.audio_url,
            "transcript": request.transcript,
            "user_id": request.user_id,
            "webhook_url": request.webhook_url,
            "start_time": time.time()
        }
        
        # Publish to practice pronunciation queue
        message_id = pubsub_client.publish_message_by_name(
            topic_name="PRACTICE_PRONUNCIATION_REQUEST",
            message=message_data
        )
        
        logger.info(f"📤 Published practice pronunciation request - Message ID: {message_id}")
        
        return PracticeSubmissionResponse(
            request_id=request_id,
            status="submitted",
            message="Practice pronunciation analysis submitted successfully. Results will be delivered via webhook.",
            estimated_processing_time_seconds="5-10"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error submitting practice pronunciation request: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to submit pronunciation analysis: {str(e)}"
        )


@router.get("/status/{request_id}", response_model=PracticeStatusResponse)
async def get_practice_status(request_id: str):
    """
    Check the status of a practice pronunciation analysis request.
    
    Use this endpoint to poll for results when you don't have a webhook URL.
    """
    try:
        logger.info(f"🔍 Checking status for practice request: {request_id}")
        
        # Check if result is available in results store
        result = await results_store.get_result(
            request_id=request_id,
            result_type="practice_pronunciation"
        )
        
        if result:
            logger.info(f"✅ Found completed result for request: {request_id}")
            
            # Convert result to PracticePronunciationResponse format
            practice_result = PracticePronunciationResponse(
                overall_pronunciation_score=result.get("overall_pronunciation_score", 0),
                accuracy_score=result.get("accuracy_score", 0),
                fluency_score=result.get("fluency_score", 0),
                prosody_score=result.get("prosody_score", 0),
                completeness_score=result.get("completeness_score", 0),
                word_details=result.get("word_details", []),
                critical_errors=result.get("critical_errors", []),
                improvement_suggestions=result.get("improvement_suggestions", ""),
                processing_time_ms=result.get("processing_time_ms", 0),
                audio_duration_seconds=result.get("audio_duration_seconds", 0),
                transcript_used=result.get("transcript_used", "")
            )
            
            return PracticeStatusResponse(
                request_id=request_id,
                status="completed",
                result=practice_result,
                error=None,
                created_at=result.get("created_at"),
                completed_at=result.get("completed_at")
            )
        else:
            logger.info(f"⏳ No result found for request: {request_id} - still processing")
            
            return PracticeStatusResponse(
                request_id=request_id,
                status="processing",
                result=None,
                error=None,
                created_at=None,
                completed_at=None
            )
            
    except Exception as e:
        logger.error(f"❌ Error checking practice status: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to check status: {str(e)}"
        )


@router.post("/analyze-pronunciation-sync", response_model=PracticePronunciationResponse)
async def analyze_pronunciation_sync(request: PracticePronunciationRequest):
    """
    TESTING ONLY: Synchronous practice pronunciation analysis.
    
    This endpoint processes the audio immediately and returns results.
    Use this for testing when you don't want to set up webhooks.
    """
    start_time = time.time()
    temp_files = []
    
    try:
        logger.info(f"🧪 [TEST] Starting synchronous practice pronunciation analysis")
        logger.info(f"🔗 Audio URL: {request.audio_url}")
        logger.info(f"📝 Transcript: {request.transcript[:100]}...")
        
        # Validate inputs
        if not request.audio_url or not request.audio_url.strip():
            raise HTTPException(status_code=400, detail="Audio URL cannot be empty")
        if not request.transcript or not request.transcript.strip():
            raise HTTPException(status_code=400, detail="Transcript cannot be empty")
        if not request.audio_url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Audio URL must be a valid HTTP/HTTPS URL")
        
        # Download audio
        session_id = str(uuid.uuid4())
        temp_audio_path = await AudioService.download_audio(request.audio_url)
        temp_files.append(temp_audio_path)
        logger.info(f"📁 Downloaded audio to: {temp_audio_path}")
        
        # Convert to WAV if needed
        if not temp_audio_path.endswith('.wav'):
            wav_path = await AudioService.convert_webm_to_wav(temp_audio_path)
            temp_files.append(wav_path)
            logger.info(f"🎵 Converted to WAV: {wav_path}")
        else:
            wav_path = temp_audio_path
        
        # Analyze pronunciation
        logger.info(f"🔍 Starting pronunciation analysis")
        result = await PronunciationService.analyze_pronunciation(
            audio_file=wav_path,
            reference_text=request.transcript,
            session_id=session_id
        )
        
        # Process results
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        if result:
            logger.info(f"✅ [TEST] Analysis completed in {processing_time_ms}ms")
            
            return PracticePronunciationResponse(
                overall_pronunciation_score=result.get("grade", 0),
                accuracy_score=result.get("accuracy_score", 0),
                fluency_score=result.get("fluency_score", 0),
                prosody_score=result.get("prosody_score", 0),
                completeness_score=result.get("completeness_score", 0),
                word_details=result.get("word_details", []),
                critical_errors=result.get("critical_errors", []),
                improvement_suggestions=result.get("improvement_suggestions", ""),
                processing_time_ms=processing_time_ms,
                audio_duration_seconds=result.get("audio_duration", 0),
                transcript_used=request.transcript
            )
        else:
            raise HTTPException(status_code=500, detail="Analysis failed")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [TEST] Error in sync analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        # Clean up temp files
        for temp_file in temp_files:
            try:
                if temp_file and os.path.exists(temp_file):
                    os.unlink(temp_file)
            except:
                pass


@router.get("/health")
async def health_check():
    """Health check endpoint for practice service"""
    return {"status": "healthy", "service": "practice"} 