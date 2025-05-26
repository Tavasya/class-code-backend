from fastapi import APIRouter, Request
from typing import Dict
from app.pubsub.webhooks.audio_webhook import AudioWebhook
from app.pubsub.webhooks.transcription_webhook import TranscriptionWebhook
from app.pubsub.webhooks.analysis_webhook import AnalysisWebhook
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize webhook handlers
audio_webhook = AudioWebhook()
transcription_webhook = TranscriptionWebhook()
analysis_webhook = AnalysisWebhook()

@router.post("/student-submission-audio")
async def handle_student_submission_audio_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for student submission audio processing.
    Triggered by student-submission-topic-sub for audio processing.
    """
    logger.info("Received student submission webhook for audio processing")
    return await audio_webhook.handle_student_submission_webhook(request)

@router.post("/student-submission-transcription")
async def handle_student_submission_transcription_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for student submission transcription processing.
    Triggered by student-submission-topic-sub for transcription processing.
    """
    logger.info("Received student submission webhook for transcription processing")
    return await transcription_webhook.handle_student_submission_webhook(request)

@router.post("/audio-conversion-done")
async def handle_audio_conversion_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for audio conversion completion.
    Triggered by audio-conversion-service-sub.
    """
    logger.info("Received audio conversion done webhook")
    return await analysis_webhook.handle_audio_conversion_done_webhook(request)

@router.post("/transcription-done")
async def handle_transcription_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for transcription completion.
    Triggered by transcription-service-sub.
    """
    logger.info("Received transcription done webhook")
    return await analysis_webhook.handle_transcription_done_webhook(request)

@router.post("/question-analysis-ready")
async def handle_question_analysis_ready_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for question analysis ready.
    Triggered by question-analysis-ready-topic-sub.
    """
    logger.info("Received question analysis ready webhook")
    return await analysis_webhook.handle_question_analysis_ready_webhook(request)

@router.post("/fluency-done")
async def handle_fluency_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for fluency analysis completion.
    Triggered by fluency-done-topic-sub.
    """
    logger.info("Received fluency done webhook")
    return await analysis_webhook.handle_fluency_done_webhook(request)

@router.post("/grammar-done")
async def handle_grammar_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for grammar analysis completion.
    Triggered by grammer-done-topic-sub.
    """
    logger.info("Received grammar done webhook")
    return await analysis_webhook.handle_grammar_done_webhook(request)

@router.post("/lexical-done")
async def handle_lexical_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for lexical analysis completion.
    Triggered by lexical-done-topic-sub.
    """
    logger.info("Received lexical done webhook")
    return await analysis_webhook.handle_lexical_done_webhook(request)

@router.post("/pronunciation-done")
async def handle_pronunciation_done_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for pronunciation analysis completion.
    Triggered by pronoun-done-topic-sub.
    NOW TRIGGERS FLUENCY ANALYSIS (Phase 2).
    """
    logger.info("Received pronunciation done webhook - triggering fluency analysis")
    return await analysis_webhook.handle_pronunciation_done_webhook(request)

@router.post("/analysis-complete")
async def handle_analysis_complete_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for complete analysis completion.
    Triggered by analysis-complete-topic-sub.
    """
    logger.info("Received analysis complete webhook")
    return await analysis_webhook.handle_analysis_complete_webhook(request)

@router.post("/submission-analyis-complete")
async def handle_submission_analysis_complete_webhook(request: Request) -> Dict[str, str]:
    """
    Webhook endpoint for complete submission analysis.
    Triggered when ALL questions in a submission are analyzed.
    Triggered by submission-analyis-complete-topic-sub.
    """
    logger.info("Received submission analysis complete webhook")
    return await analysis_webhook.handle_submission_analysis_complete_webhook(request) 