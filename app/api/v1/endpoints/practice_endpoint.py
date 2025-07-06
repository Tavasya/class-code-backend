from fastapi import APIRouter, HTTPException, Path
from app.services.practice_session_service import PracticeSessionService
from app.services.transcription_service import TranscriptionService
from app.services.paragraph_restructuring_service import restructure_paragraph
import logging
from typing import Dict, Any
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class ImproveTranscriptResponse(BaseModel):
    """Response model for improve transcript endpoint"""
    success: bool
    message: str
    session_id: str
    status: str

@router.post("/sessions/{session_id}/improve-transcript", response_model=ImproveTranscriptResponse)
async def improve_session_transcript(
    session_id: str = Path(..., description="Practice session ID")
) -> ImproveTranscriptResponse:
    """
    Improve transcript for an existing practice session
    
    This endpoint:
    1. Reads the session from the database using session_id
    2. Validates the session exists and has an audio_url
    3. Transcribes the audio using existing TranscriptionService
    4. Improves the transcript using existing ParagraphRestructuringService
    5. Updates the session with improved transcript and status='transcript_ready'
    6. Returns a success response
    
    Args:
        session_id: The practice session ID (from URL path)
        
    Returns:
        ImproveTranscriptResponse with success status and session info
    """
    try:
        logger.info(f"🎯 Starting transcript improvement for session: {session_id}")
        
        # Initialize services
        practice_service = PracticeSessionService()
        transcription_service = TranscriptionService()
        
        # 1. Read session from database
        session = practice_service.get_practice_session(session_id)
        if not session:
            logger.error(f"❌ Session not found: {session_id}")
            raise HTTPException(
                status_code=404, 
                detail=f"Practice session not found: {session_id}"
            )
        
        # 2. Validate session has original_audio_url
        audio_url = session.get('original_audio_url')
        if not audio_url:
            logger.error(f"❌ Session {session_id} has no original_audio_url")
            raise HTTPException(
                status_code=400, 
                detail=f"Session {session_id} has no audio URL"
            )
        
        logger.info(f"📱 Found session with audio URL: {audio_url}")
        
        # 3. Transcribe audio
        logger.info(f"🎤 Transcribing audio from URL: {audio_url}")
        transcription_result = await transcription_service.transcribe_audio_from_url(audio_url)
        
        if transcription_result.get("error"):
            logger.error(f"❌ Transcription failed: {transcription_result['error']}")
            raise HTTPException(
                status_code=400,
                detail=f"Audio transcription failed: {transcription_result['error']}"
            )
        
        transcript = transcription_result.get("text", "").strip()
        if not transcript:
            logger.error(f"❌ Empty transcript from audio")
            raise HTTPException(
                status_code=400,
                detail="Transcription resulted in empty text"
            )
        
        logger.info(f"📝 Transcribed text: {transcript[:100]}...")
        
        # 4. Improve transcript using paragraph restructuring
        logger.info(f"🔄 Improving transcript using paragraph restructuring")
        restructuring_result = await restructure_paragraph(
            transcript=transcript,
            current_band=None,  # Will auto-detect or default to A1
            analysis_results=None  # Will use default fallback
        )
        
        improved_transcript = restructuring_result.improved_transcript
        logger.info(f"✨ Improved transcript: {improved_transcript[:100]}...")
        
        # 5. Update session with improved transcript and status
        update_success = practice_service.update_practice_session(
            session_id=session_id,
            original_transcript=transcript,
            improved_transcript=improved_transcript,
            status="transcript_ready"
        )
        
        if not update_success:
            logger.error(f"❌ Failed to update session {session_id}")
            raise HTTPException(
                status_code=500,
                detail="Failed to update session with improved transcript"
            )
        
        logger.info(f"✅ Successfully improved transcript for session: {session_id}")
        
        # 6. Return success response
        return ImproveTranscriptResponse(
            success=True,
            message="Transcript improved successfully",
            session_id=session_id,
            status="transcript_ready"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"❌ Unexpected error improving transcript for session {session_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for practice service"""
    return {"status": "healthy", "service": "practice"}