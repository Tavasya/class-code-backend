from fastapi import FastAPI
import uvicorn
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CORS_ORIGINS
from app.api.v1.router import api_router
from app.services.file_manager_service import file_manager
import logging

logger = logging.getLogger(__name__)

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

# Background task for periodic file cleanup
cleanup_task = None

@app.on_event("startup")
async def startup_event():
    """Start periodic cleanup task for file management"""
    global cleanup_task
    
    async def periodic_cleanup_loop():
        """Run periodic cleanup every 5 minutes"""
        while True:
            try:
                await asyncio.sleep(300)  # Sleep for 5 minutes
                await file_manager.periodic_cleanup()
                logger.info("Completed periodic file cleanup")
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {str(e)}")
    
    cleanup_task = asyncio.create_task(periodic_cleanup_loop())
    logger.info("Started periodic file cleanup task")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background tasks"""
    global cleanup_task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        logger.info("Stopped periodic file cleanup task")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)