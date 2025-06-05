from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.vocabulary_service import analyze_vocabulary
from app.models.vocabulary_model import VocabularyFeedback
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/analyze", response_model=VocabularyFeedback)
async def analyze_vocabulary_endpoint(transcript: str) -> Dict[str, Any]:
    """
    Analyze vocabulary in a transcript.
    
    Args:
        transcript (str): The transcript text to analyze
        
    Returns:
        VocabularyFeedback: Vocabulary analysis results including:
            - grade: float - A score based on the number of vocabulary suggestions
            - vocabulary_suggestions: Dict[str, VocabularySuggestion] - Dictionary of vocabulary suggestions
                indexed by their position in the text
    """
    try:
        logger.info("Starting vocabulary analysis")
        result = await analyze_vocabulary(transcript)
        logger.info("Vocabulary analysis completed successfully")
        return result
    except Exception as e:
        logger.error(f"Error in vocabulary analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Vocabulary analysis failed: {str(e)}") 