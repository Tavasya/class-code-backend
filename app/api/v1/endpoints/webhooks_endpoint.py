from fastapi import APIRouter, Request
from typing import Dict
from app.pubsub.webhooks.submission_webhook import SubmissionWebhook
from app.pubsub.webhooks.analysis_webhook import AnalysisWebhook
from app.pubsub.utils import safe_webhook_handler
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize webhook handlers
submission_webhook = SubmissionWebhook()
analysis_webhook = AnalysisWebhook()

@router.post("/student-submission")
@safe_webhook_handler
async def handle_student_submission_webhook(request: Request) -> Dict[str, str]:
    """
    Unified webhook endpoint for student submission processing.
    Handles BOTH audio and transcription processing in parallel.
    Triggered by student-submission-topic-sub.
    """
    logger.info("Received student submission webhook - starting parallel audio and transcription processing")
    return await submission_webhook.handle_student_submission_webhook(request)

@router.post("/audio-conversion-done")
@safe_webhook_handler
async def handle_audio_conversion_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for audio conversion completion.
    Triggered by audio-conversion-service-sub.
    """
    logger.info("Received audio conversion done webhook")
    return await analysis_webhook.handle_audio_conversion_done_webhook(request)

@router.post("/transcription-done")
@safe_webhook_handler
async def handle_transcription_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for transcription completion.
    Triggered by transcription-service-sub.
    """
    logger.info("Received transcription done webhook")
    return await analysis_webhook.handle_transcription_done_webhook(request)

@router.post("/question-analysis-ready")
@safe_webhook_handler
async def handle_question_analysis_ready_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for question analysis ready.
    Triggered by question-analysis-ready-topic-sub.
    """
    logger.info("Received question analysis ready webhook")
    return await analysis_webhook.handle_question_analysis_ready_webhook(request)

@router.post("/fluency-done")
@safe_webhook_handler
async def handle_fluency_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for fluency analysis completion.
    Triggered by fluency-done-topic-sub.
    """
    logger.info("Received fluency done webhook")
    return await analysis_webhook.handle_fluency_done_webhook(request)

@router.post("/grammar-done")
@safe_webhook_handler
async def handle_grammar_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for grammar analysis completion.
    Triggered by grammer-done-topic-sub.
    """
    logger.info("Received grammar done webhook")
    return await analysis_webhook.handle_grammar_done_webhook(request)

@router.post("/lexical-done")
@safe_webhook_handler
async def handle_lexical_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for lexical analysis completion.
    Triggered by lexical-done-topic-sub.
    """
    logger.info("Received lexical done webhook")
    return await analysis_webhook.handle_lexical_done_webhook(request)

@router.post("/pronunciation-done")
@safe_webhook_handler
async def handle_pronunciation_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for pronunciation analysis completion.
    Triggered by pronoun-done-topic-sub.
    NOW TRIGGERS FLUENCY ANALYSIS (Phase 2).
    """
    logger.info("Received pronunciation done webhook - triggering fluency analysis")
    return await analysis_webhook.handle_pronunciation_done_webhook(request)

@router.post("/analysis-complete")
@safe_webhook_handler
async def handle_analysis_complete_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for complete analysis completion.
    Triggered by analysis-complete-topic-sub.
    """
    logger.info("Received analysis complete webhook")
    return await analysis_webhook.handle_analysis_complete_webhook(request)

@router.post("/submission-analyis-complete")
@safe_webhook_handler
async def handle_submission_analysis_complete_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for complete submission analysis.
    Triggered when ALL questions in a submission are analyzed.
    Triggered by submission-analyis-complete-topic-sub.
    """
    logger.info("Received submission analysis complete webhook")
    return await analysis_webhook.handle_submission_analysis_complete_webhook(request)

@router.post("/vocabulary-done")
@safe_webhook_handler
async def handle_vocabulary_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for vocabulary analysis completion.
    Triggered by vocabulary-done-topic-sub.
    """
    logger.info("Received vocabulary done webhook")
    return await analysis_webhook.handle_vocabulary_done_webhook(request) 