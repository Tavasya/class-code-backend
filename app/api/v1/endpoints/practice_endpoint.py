from fastapi import APIRouter, HTTPException, Path
from app.services.practice_session_service import PracticeSessionService
from app.services.sentence_extraction_service import SentenceExtractionService
from app.services.practice_webhook_service import PracticeWebhookService
import logging
from typing import Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class StartPracticeResponse(BaseModel):
    """Response model for start practice endpoint"""
    success: bool
    message: str
    session_id: str
    status: str
    current_sentence: Dict[str, Any]
    webhook_session_id: str

class SentencePracticeRequest(BaseModel):
    """Request model for sentence practice submission"""
    sentence_index: int
    audio_url: str

class SentencePracticeResponse(BaseModel):
    """Response model for sentence practice submission"""
    success: bool
    message: str
    session_id: str
    sentence_index: int
    analysis_submitted: bool
    webhook_session_id: str

class WordPracticeRequest(BaseModel):
    """Request model for word practice submission"""
    word: str
    audio_url: str

class WordPracticeResponse(BaseModel):
    """Response model for word practice submission"""
    success: bool
    message: str
    session_id: str
    word: str
    analysis_submitted: bool
    webhook_session_id: str

class PracticeProgressResponse(BaseModel):
    """Response model for practice progress endpoint"""
    success: bool
    session_id: str
    status: str
    current_content: Dict[str, Any]
    progress: Dict[str, Any]
    webhook_session_id: str

class PracticeStatusResponse(BaseModel):
    """Response model for practice status endpoint"""
    success: bool
    session_id: str
    status: str
    webhook_session_id: str

@router.post("/sessions/{session_id}/start-practice", response_model=StartPracticeResponse)
async def start_practice_session(
    session_id: str = Path(..., description="Practice session ID")
) -> StartPracticeResponse:
    """
    Start pronunciation practice for a session with a user-provided transcript
    
    This endpoint:
    1. Validates the session exists and has a transcript
    2. Extracts sentences from the transcript
    3. Updates session with sentences and status='practicing_sentences'
    4. Sets current_sentence_index to 0
    5. Returns first sentence for practice
    
    Args:
        session_id: The practice session ID (from URL path)
        
    Returns:
        StartPracticeResponse with first sentence and practice metadata
    """
    try:
        logger.info(f"🎯 Starting practice for session: {session_id}")
        
        # Initialize services
        practice_service = PracticeSessionService()
        sentence_service = SentenceExtractionService()
        webhook_service = PracticeWebhookService()
        
        # 1. Read session from database
        session = practice_service.get_practice_session(session_id)
        if not session:
            logger.error(f"❌ Session not found: {session_id}")
            raise HTTPException(
                status_code=404, 
                detail=f"Practice session not found: {session_id}"
            )
        
        # 2. Validate session has improved transcript
        transcript = session.get('improved_transcript')
        if not transcript:
            logger.error(f"❌ Session {session_id} has no improved transcript")
            raise HTTPException(
                status_code=400, 
                detail=f"Session {session_id} has no improved transcript for practice"
            )
        
        logger.info(f"📝 Found session with transcript: {transcript[:100]}...")
        
        # 3. Extract sentences from transcript
        logger.info(f"🔍 Extracting sentences from transcript")
        sentences = sentence_service.extract_sentences(transcript)
        
        if not sentences:
            logger.error(f"❌ No sentences extracted from transcript")
            raise HTTPException(
                status_code=400,
                detail="No sentences could be extracted from the transcript"
            )
        
        logger.info(f"📚 Extracted {len(sentences)} sentences for practice")
        
        # 4. Start webhook session for real-time pronunciation analysis
        logger.info(f"🎯 Starting webhook session for practice")
        webhook_session_id = webhook_service.start_practice_webhook_session(
            session_id=session_id,
            transcript=transcript
        )
        
        if not webhook_session_id:
            logger.error(f"❌ Failed to start webhook session for {session_id}")
            raise HTTPException(
                status_code=500,
                detail="Failed to start webhook session for practice"
            )
        
        logger.info(f"✅ Webhook session started: {webhook_session_id}")
        
        # 5. Update session with sentences, webhook session, and practice status
        update_success = practice_service.update_practice_session(
            session_id=session_id,
            sentences=sentences,
            current_sentence_index=0,
            current_word_index=0,
            status="practicing_sentences",
            webhook_session_id=webhook_session_id
        )
        
        if not update_success:
            logger.error(f"❌ Failed to update session {session_id}")
            raise HTTPException(
                status_code=500,
                detail="Failed to update session for practice"
            )
        
        # 6. Get first sentence for response
        first_sentence = sentences[0] if sentences else {"text": "", "index": 0}
        
        logger.info(f"✅ Successfully started practice for session: {session_id}")
        
        # 7. Return success response
        return StartPracticeResponse(
            success=True,
            message="Practice session started successfully",
            session_id=session_id,
            status="practicing_sentences",
            current_sentence=first_sentence,
            webhook_session_id=webhook_session_id
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"❌ Unexpected error starting practice for session {session_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@router.post("/sessions/{session_id}/sentences", response_model=SentencePracticeResponse)
async def submit_sentence_practice(
    session_id: str = Path(..., description="Practice session ID"),
    request: SentencePracticeRequest = None
) -> SentencePracticeResponse:
    """
    Submit a sentence recording for pronunciation analysis
    
    This endpoint:
    1. Validates the practice session exists and is in practicing_sentences status
    2. Validates the sentence index is valid
    3. Submits the audio to the webhook service for analysis
    4. Returns confirmation that analysis was submitted
    
    Args:
        session_id: The practice session ID (from URL path)
        request: Sentence practice request with sentence_index and audio_url
        
    Returns:
        SentencePracticeResponse confirming submission
    """
    try:
        logger.info(f"🎤 Submitting sentence practice for session: {session_id}")
        logger.info(f"📝 Sentence index: {request.sentence_index}, Audio: {request.audio_url}")
        
        # Initialize services
        practice_service = PracticeSessionService()
        webhook_service = PracticeWebhookService()
        
        # 1. Read session from database
        session = practice_service.get_practice_session(session_id)
        if not session:
            logger.error(f"❌ Session not found: {session_id}")
            raise HTTPException(
                status_code=404, 
                detail=f"Practice session not found: {session_id}"
            )
        
        # 2. Validate session status
        current_status = session.get('status')
        if current_status != 'practicing_sentences':
            logger.error(f"❌ Session {session_id} has incorrect status: {current_status}")
            raise HTTPException(
                status_code=400, 
                detail=f"Session {session_id} must be in 'practicing_sentences' status, got '{current_status}'"
            )
        
        # 3. Validate webhook session exists
        webhook_session_id = session.get('webhook_session_id')
        if not webhook_session_id:
            logger.error(f"❌ Session {session_id} has no webhook session")
            raise HTTPException(
                status_code=400,
                detail=f"Session {session_id} has no active webhook session"
            )
        
        # 4. Validate sentence index and get sentence
        sentences = session.get('sentences', [])
        if not (0 <= request.sentence_index < len(sentences)):
            logger.error(f"❌ Invalid sentence index: {request.sentence_index}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid sentence index {request.sentence_index}. Valid range: 0-{len(sentences)-1}"
            )
        
        current_sentence = sentences[request.sentence_index]
        sentence_text = current_sentence['text']
        
        logger.info(f"📚 Practicing sentence: {sentence_text}")
        
        # 5. Submit to webhook service for analysis
        submission_success = webhook_service.submit_sentence_for_analysis(
            session_id=session_id,
            webhook_session_id=webhook_session_id,
            sentence_index=request.sentence_index,
            sentence_text=sentence_text,
            audio_url=request.audio_url
        )
        
        if not submission_success:
            logger.error(f"❌ Failed to submit sentence for analysis")
            raise HTTPException(
                status_code=500,
                detail="Failed to submit sentence for pronunciation analysis"
            )
        
        logger.info(f"✅ Sentence submitted for analysis successfully")
        
        # 6. Return success response
        return SentencePracticeResponse(
            success=True,
            message="Sentence submitted for analysis",
            session_id=session_id,
            sentence_index=request.sentence_index,
            analysis_submitted=True,
            webhook_session_id=webhook_session_id
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"❌ Unexpected error submitting sentence practice for session {session_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/sessions/{session_id}/progress", response_model=PracticeProgressResponse)
async def get_practice_progress(
    session_id: str = Path(..., description="Practice session ID")
) -> PracticeProgressResponse:
    """
    Get current practice progress and next content to practice
    
    This endpoint:
    1. Returns current practice session status and progress
    2. Identifies what content should be practiced next (sentence/word)
    3. Provides progress metrics
    
    Args:
        session_id: The practice session ID (from URL path)
        
    Returns:
        PracticeProgressResponse with current state and progress
    """
    try:
        logger.info(f"📊 Getting practice progress for session: {session_id}")
        
        # Initialize service
        practice_service = PracticeSessionService()
        
        # 1. Read session from database
        session = practice_service.get_practice_session(session_id)
        if not session:
            logger.error(f"❌ Session not found: {session_id}")
            raise HTTPException(
                status_code=404, 
                detail=f"Practice session not found: {session_id}"
            )
        
        # 2. Get current practice content
        current_content = practice_service.get_current_practice_content(session_id)
        if not current_content:
            logger.error(f"❌ No current practice content for session: {session_id}")
            raise HTTPException(
                status_code=400,
                detail="No current practice content available"
            )
        
        # 3. Get detailed progress
        progress = practice_service.get_practice_progress(session_id)
        if not progress:
            logger.error(f"❌ Failed to get progress for session: {session_id}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve practice progress"
            )
        
        # 4. Get webhook session info
        webhook_session_id = session.get('webhook_session_id', '')
        current_status = session.get('status', 'unknown')
        
        logger.info(f"✅ Retrieved practice progress for session: {session_id}")
        
        # 5. Return progress response
        return PracticeProgressResponse(
            success=True,
            session_id=session_id,
            status=current_status,
            current_content=current_content,
            progress=progress,
            webhook_session_id=webhook_session_id
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"❌ Unexpected error getting practice progress for session {session_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@router.post("/sessions/{session_id}/words", response_model=WordPracticeResponse)
async def submit_word_practice(
    session_id: str = Path(..., description="Practice session ID"),
    request: WordPracticeRequest = None
) -> WordPracticeResponse:
    """
    Submit a word recording for pronunciation analysis
    
    This endpoint:
    1. Validates the practice session exists and is in practicing_words status
    2. Validates the word is in the current problematic words list
    3. Submits the audio to the webhook service for analysis
    4. Returns confirmation that analysis was submitted
    
    Args:
        session_id: The practice session ID (from URL path)
        request: Word practice request with word and audio_url
        
    Returns:
        WordPracticeResponse confirming submission
    """
    try:
        logger.info(f"🔤 Submitting word practice for session: {session_id}")
        logger.info(f"📝 Word: {request.word}, Audio: {request.audio_url}")
        
        # Initialize services
        practice_service = PracticeSessionService()
        webhook_service = PracticeWebhookService()
        
        # 1. Read session from database
        session = practice_service.get_practice_session(session_id)
        if not session:
            logger.error(f"❌ Session not found: {session_id}")
            raise HTTPException(
                status_code=404, 
                detail=f"Practice session not found: {session_id}"
            )
        
        # 2. Validate session status
        current_status = session.get('status')
        if current_status != 'practicing_words':
            logger.error(f"❌ Session {session_id} has incorrect status: {current_status}")
            raise HTTPException(
                status_code=400, 
                detail=f"Session {session_id} must be in 'practicing_words' status, got '{current_status}'"
            )
        
        # 3. Validate webhook session exists
        webhook_session_id = session.get('webhook_session_id')
        if not webhook_session_id:
            logger.error(f"❌ Session {session_id} has no webhook session")
            raise HTTPException(
                status_code=400,
                detail=f"Session {session_id} has no active webhook session"
            )
        
        # 4. Validate word is in problematic words list
        problematic_words = session.get('problematic_words', [])
        current_word_index = session.get('current_word_index', 0)
        
        if not (0 <= current_word_index < len(problematic_words)):
            logger.error(f"❌ Invalid word index: {current_word_index}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid word index {current_word_index}. Valid range: 0-{len(problematic_words)-1}"
            )
        
        current_word_data = problematic_words[current_word_index]
        expected_word = current_word_data.get('word', '').lower()
        submitted_word = request.word.lower()
        
        if expected_word != submitted_word:
            logger.error(f"❌ Word mismatch. Expected: {expected_word}, Got: {submitted_word}")
            raise HTTPException(
                status_code=400,
                detail=f"Expected word '{expected_word}' but got '{submitted_word}'"
            )
        
        sentence_context = current_word_data.get('sentence_context', '')
        
        logger.info(f"📚 Practicing word: {expected_word} in context: {sentence_context}")
        
        # 5. Submit to webhook service for analysis
        submission_success = webhook_service.submit_word_for_analysis(
            session_id=session_id,
            webhook_session_id=webhook_session_id,
            word=expected_word,
            sentence_context=sentence_context,
            audio_url=request.audio_url
        )
        
        if not submission_success:
            logger.error(f"❌ Failed to submit word for analysis")
            raise HTTPException(
                status_code=500,
                detail="Failed to submit word for pronunciation analysis"
            )
        
        logger.info(f"✅ Word submitted for analysis successfully")
        
        # 6. Return success response
        return WordPracticeResponse(
            success=True,
            message="Word submitted for analysis",
            session_id=session_id,
            word=expected_word,
            analysis_submitted=True,
            webhook_session_id=webhook_session_id
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception(f"❌ Unexpected error submitting word practice for session {session_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/sessions/{session_id}/status", response_model=PracticeStatusResponse)
async def get_practice_status(
    session_id: str = Path(..., description="Practice session ID")
) -> PracticeStatusResponse:
    """
    Get practice session status
    
    This endpoint returns the current status of a practice session
    without the detailed progress information.
    
    Args:
        session_id: The practice session ID (from URL path)
        
    Returns:
        PracticeStatusResponse with session status
    """
    try:
        logger.info(f"📊 Getting practice status for session: {session_id}")
        
        # Initialize service
        practice_service = PracticeSessionService()
        
        # Get session from database
        session = practice_service.get_practice_session(session_id)
        if not session:
            logger.error(f"❌ Session not found: {session_id}")
            raise HTTPException(
                status_code=404, 
                detail=f"Practice session not found: {session_id}"
            )
        
        # Extract status and webhook session
        current_status = session.get('status', 'unknown')
        webhook_session_id = session.get('webhook_session_id', '')
        
        logger.info(f"✅ Retrieved practice status for session: {session_id}")
        
        return PracticeStatusResponse(
            success=True,
            session_id=session_id,
            status=current_status,
            webhook_session_id=webhook_session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ Unexpected error getting practice status for session {session_id}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error: {str(e)}"
        )

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for practice service"""
    return {"status": "healthy", "service": "practice"}