from fastapi import FastAPI
import uvicorn
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CORS_ORIGINS
from app.api.v1.router import api_router
from app.pubsub.handlers import SubscriberHandler

app = FastAPI(title="Audio Analysis API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Start the subscriber handler when the application starts"""
    subscriber_handler = SubscriberHandler()
    asyncio.create_task(subscriber_handler.start_listening())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)