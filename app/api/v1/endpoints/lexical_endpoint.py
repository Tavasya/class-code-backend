from fastapi import APIRouter, HTTPException
from typing import List
from app.models.lexical_model import LexicalAnalysisResponse
from app.services.lexical_service import analyze_lexical_resources

router = APIRouter()

@router.post("/analyze", response_model=LexicalAnalysisResponse)
async def analyze_lexical(text: str):
    """
    Analyze lexical resources in the provided text.
    
    Args:
        text: The text to analyze
        
    Returns:
        LexicalAnalysisResponse containing feedback for each sentence
    """
    try:
        # Split text into sentences (you might want to use a more sophisticated sentence splitter)
        sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        if not sentences:
            return LexicalAnalysisResponse(
                lexical_feedback=[],
                error="No valid sentences found in the input text"
            )
        
        # Get lexical feedback
        feedback = await analyze_lexical_resources(sentences)
        
        return LexicalAnalysisResponse(
            lexical_feedback=feedback
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing lexical resources: {str(e)}"
        ) 