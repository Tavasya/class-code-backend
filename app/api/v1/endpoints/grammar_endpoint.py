from fastapi import APIRouter, HTTPException
from app.models.grammer_model import GrammarRequest, GrammarResponse
from app.services.grammar_service import analyze_grammar
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/analysis", response_model=GrammarResponse)
async def analyze_grammar_endpoint(request: GrammarRequest):
    """
    Analyze grammar and vocabulary in a transcript
    
    Args:
        request: GrammarRequest containing the transcript to analyze
        
    Returns:
        GrammarResponse containing grammar corrections and vocabulary suggestions
    """
    try:
        logger.info(f"Received grammar analysis request for transcript of length: {len(request.transcript)}")
        
        if not request.transcript or len(request.transcript.strip()) < 10:
            raise HTTPException(
                status_code=400,
                detail="Transcript is too short for analysis (minimum 10 characters)"
            )
        
        # Run the grammar analysis
        result = await analyze_grammar(request.transcript)
        
        # Create response
        response = GrammarResponse(
            status="success",
            grammar_corrections=result["grammar_corrections"],
            vocabulary_suggestions=result["vocabulary_suggestions"]
        )
        
        # Log statistics
        grammar_count = len(result["grammar_corrections"])
        vocab_count = len(result["vocabulary_suggestions"])
        logger.info(f"Analysis complete: {grammar_count} grammar issues, {vocab_count} vocabulary suggestions")
        
        return response
        
    except HTTPException:
        # Re-raise HTTPException to preserve status code
        raise
    except Exception as e:
        logger.exception("Error in grammar analysis endpoint")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing grammar: {str(e)}"
        )
