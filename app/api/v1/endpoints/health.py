from fastapi import APIRouter
from datetime import datetime
import os
from app.core.config import supabase
from app.models.schemas import HealthResponse

router = APIRouter()

@router.get("/", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    supabase_status = "connected" if supabase else "not connected"
    
    return {
        "status": "STAGE BRANCH ISS HEALTHYY",
        "timestamp": datetime.now().isoformat(),
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "supabase": supabase_status
    }