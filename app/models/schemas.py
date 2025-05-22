from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    environment: str
    supabase: str


    
    