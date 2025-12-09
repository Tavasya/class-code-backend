from fastapi import FastAPI
import uvicorn
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import CORS_ORIGINS
from app.api.v1.router import api_router
from app.services.file_manager_service import file_manager
from app.services.openai_client import close_openai_client
import logging
from app.utils.vocabulary_utils import initialize_vocabulary_tools
import sentry_sdk

# Initialize Sentry SDK
sentry_sdk.init(
    dsn="https://1f8ebec20c93a839d96da4a9f009c676@o4509532792815616.ingest.us.sentry.io/4509532796747776",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
    # Capture 100% of the transactions for performance monitoring.
    # We recommend adjusting this value in production.
    traces_sample_rate=1.0,
)

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
        """Run periodic cleanup every 15 minutes"""
        while True:
            try:
                await asyncio.sleep(900)  # Sleep for 15 minutes (less aggressive)
                await file_manager.periodic_cleanup()
                logger.info("Completed periodic file cleanup")
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {str(e)}")
    
    cleanup_task = asyncio.create_task(periodic_cleanup_loop())
    logger.info("Started periodic file cleanup task")

    # Initialize vocabulary enhancement tools
    try:
        logger.info("Initializing vocabulary tools...")
        initialize_vocabulary_tools()
        logger.info("Successfully initialized vocabulary tools")
    except Exception as e:
        logger.error(f"Failed to initialize vocabulary tools: {str(e)}")
        # Don't raise the error, just log it and continue
        # This allows the application to start even if vocabulary tools fail
        logger.warning("Application will continue without vocabulary tools")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background tasks and connections"""
    global cleanup_task
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        logger.info("Stopped periodic file cleanup task")

    # Close shared OpenAI client connection pool
    await close_openai_client()
    logger.info("Closed OpenAI client connection pool")

@app.get("/sentry-debug")
async def trigger_error():
    """Sentry debug endpoint to verify installation by triggering an error"""
    division_by_zero = 1 / 0

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)