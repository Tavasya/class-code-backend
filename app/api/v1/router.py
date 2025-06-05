from fastapi import APIRouter

from .endpoints import health, audio_endpoint, transcription_endpoint, pronunciation_endpoint, fluency_endpoint, grammar_endpoint, submission_endpoint, lexical_endpoint, webhooks_endpoint, results_endpoint, debug_endpoint, vocabulary_endpoint

api_router = APIRouter()

api_router.include_router(submission_endpoint.router, prefix="/submission", tags=["gateway"])
api_router.include_router(webhooks_endpoint.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(results_endpoint.router, prefix="/results", tags=["testing"])
api_router.include_router(debug_endpoint.router, prefix="/debug", tags=["debug"])

api_router.include_router(health.router, prefix="/health", tags=["health"])

api_router.include_router(audio_endpoint.router, prefix="/audio", tags=["audio"])
api_router.include_router(transcription_endpoint.router, prefix="/transcription", tags=["audio"])

api_router.include_router(pronunciation_endpoint.router, prefix="/pronunciation", tags=["analysis"])
api_router.include_router(fluency_endpoint.router, prefix="/fluency", tags=["analysis"])
api_router.include_router(grammar_endpoint.router, prefix="/grammar", tags=["analysis"])
api_router.include_router(lexical_endpoint.router, prefix="/lexical", tags=["analysis"])
api_router.include_router(vocabulary_endpoint.router, prefix="/vocabulary", tags=["analysis"])

api_router.include_router(submission_endpoint.router, prefix="/submission", tags=["gateway"])
