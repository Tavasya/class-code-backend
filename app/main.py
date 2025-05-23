from fastapi import FastAPI
import uvicorn
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CORS_ORIGINS
from app.api.v1.router import api_router

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

# Note: Removed startup event with SubscriberHandler.start_listening()
# as the application now uses push-based webhooks instead of polling

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)