from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    environment: str
    supabase: str

class GrammarRequest(BaseModel):
    transcript: str

class GrammarResponse(BaseModel):
    grammar_corrections: Dict[str, Any]
    vocabulary_suggestions: Dict[str, Any]
    lexical_resources: Dict[str, Any]

    
    