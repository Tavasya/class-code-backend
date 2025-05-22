from fastapi import APIRouter

from .endpoints import health, audio_endpoint, transcription_endpoint

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(audio_endpoint.router, prefix="/audio", tags=["audio"])
api_router.include_router(transcription_endpoint.router, prefix="/transcription", tags=["transcription"])