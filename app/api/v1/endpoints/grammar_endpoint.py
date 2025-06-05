from fastapi import APIRouter, HTTPException
from app.models.grammar_model import GrammarRequest, GrammarResponse
from app.services.grammar_service import analyze_grammar
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/analysis", response_model=GrammarResponse)
async def analyze_grammar_endpoint(request: GrammarRequest):
    """
    Analyze grammar in a transcript
    
    Args:
        request: GrammarRequest containing the transcript to analyze
        
    Returns:
        GrammarResponse containing:
        - Grammar corrections with context
        - Overall analysis grade
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
        
        # Create response with enhanced information
        response = GrammarResponse(
            status="success",
            grammar_corrections=result["grammar_corrections"],
            grade=result.get("grade", 100),  # Include the calculated grade
            error=None  # Explicitly set error to None for successful analysis
        )
        
        # Log detailed statistics
        grammar_count = len(result["grammar_corrections"])
        grade = result.get("grade", 100)
        logger.info(f"Analysis complete: Grade={grade}, {grammar_count} grammar corrections")
        
        return response
        
    except Exception as e:
        logger.exception("Error in grammar analysis endpoint")
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing grammar: {str(e)}"
        )
