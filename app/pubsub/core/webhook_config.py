import os
import logging

logger = logging.getLogger(__name__)

# Webhook authentication token for Pub/Sub push endpoints
# In production, this should be set as an environment variable
WEBHOOK_AUTH_TOKEN = os.getenv("PUBSUB_WEBHOOK_AUTH_TOKEN", None)

# Webhook endpoint URLs for Google Cloud Pub/Sub configuration
# These should match your deployment URL + the webhook paths
BASE_WEBHOOK_URL = os.getenv("BASE_WEBHOOK_URL", "https://your-app-domain.com")

WEBHOOK_ENDPOINTS = {
    "STUDENT_SUBMISSION_AUDIO": f"{BASE_WEBHOOK_URL}/api/v1/webhooks/student-submission-audio",
    "STUDENT_SUBMISSION_TRANSCRIPTION": f"{BASE_WEBHOOK_URL}/api/v1/webhooks/student-submission-transcription",
    "AUDIO_CONVERSION_DONE": f"{BASE_WEBHOOK_URL}/api/v1/webhooks/audio-conversion-done",
    "TRANSCRIPTION_DONE": f"{BASE_WEBHOOK_URL}/api/v1/webhooks/transcription-done",
    "QUESTION_ANALYSIS_READY": f"{BASE_WEBHOOK_URL}/api/v1/webhooks/question-analysis-ready",
    "FLUENCY_DONE": f"{BASE_WEBHOOK_URL}/api/v1/webhooks/fluency-done",
    "GRAMMAR_DONE": f"{BASE_WEBHOOK_URL}/api/v1/webhooks/grammar-done",
    "LEXICAL_DONE": f"{BASE_WEBHOOK_URL}/api/v1/webhooks/lexical-done",
    "PRONUNCIATION_DONE": f"{BASE_WEBHOOK_URL}/api/v1/webhooks/pronunciation-done",
    "ANALYSIS_COMPLETE": f"{BASE_WEBHOOK_URL}/api/v1/webhooks/analysis-complete",
}

# Log webhook configuration
logger.info(f"Webhook authentication: {'Enabled' if WEBHOOK_AUTH_TOKEN else 'Disabled'}")
logger.info(f"Base webhook URL: {BASE_WEBHOOK_URL}")

# Google Cloud Pub/Sub subscription configuration for push
SUBSCRIPTION_CONFIGS = {
    "student-submission-topic-audio-sub": {
        "topic": "student-submission-topic",
        "push_endpoint": WEBHOOK_ENDPOINTS["STUDENT_SUBMISSION_AUDIO"]
    },
    "student-submission-topic-transcription-sub": {
        "topic": "student-submission-topic", 
        "push_endpoint": WEBHOOK_ENDPOINTS["STUDENT_SUBMISSION_TRANSCRIPTION"]
    },
    "audio-conversion-service-sub": {
        "topic": "audio-conversion-done-topic",
        "push_endpoint": WEBHOOK_ENDPOINTS["AUDIO_CONVERSION_DONE"]
    },
    "transcription-service-sub": {
        "topic": "transcription-done-topic",
        "push_endpoint": WEBHOOK_ENDPOINTS["TRANSCRIPTION_DONE"]
    },
    "question-analysis-ready-topic-sub": {
        "topic": "question-analysis-ready-topic",
        "push_endpoint": WEBHOOK_ENDPOINTS["QUESTION_ANALYSIS_READY"]
    },
    "fluency-done-topic-sub": {
        "topic": "fluency-done-topic",
        "push_endpoint": WEBHOOK_ENDPOINTS["FLUENCY_DONE"]
    },
    "grammer-done-topic-sub": {
        "topic": "grammer-done-topic",
        "push_endpoint": WEBHOOK_ENDPOINTS["GRAMMAR_DONE"]
    },
    "lexical-done-topic-sub": {
        "topic": "lexical-done-topic",
        "push_endpoint": WEBHOOK_ENDPOINTS["LEXICAL_DONE"]
    },
    "pronoun-done-topic-sub": {
        "topic": "pronoun-done-topic",
        "push_endpoint": WEBHOOK_ENDPOINTS["PRONUNCIATION_DONE"]
    },
    "analysis-complete-topic-sub": {
        "topic": "analysis-complete-topic",
        "push_endpoint": WEBHOOK_ENDPOINTS["ANALYSIS_COMPLETE"]
    }
} 