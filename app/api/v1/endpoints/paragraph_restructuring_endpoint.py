from fastapi import APIRouter, HTTPException
from app.models.paragraph_restructuring_model import (
    ParagraphRestructuringRequest,
    ParagraphRestructuringResponse
)
from app.services.paragraph_restructuring_service import analyze_paragraph_restructuring
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/analysis", response_model=ParagraphRestructuringResponse)
async def restructure_paragraph(request: ParagraphRestructuringRequest) -> ParagraphRestructuringResponse:
    """
    Restructure a paragraph to the next CEFR level
    
    Args:
        request: ParagraphRestructuringRequest containing transcript and optional current band
        
    Returns:
        ParagraphRestructuringResponse with original band, target band, and improved transcript
    """
    try:
        logger.info(f"Received paragraph restructuring request for transcript: {request.transcript[:100]}...")
        
        if not request.transcript or not request.transcript.strip():
            raise HTTPException(status_code=400, detail="Transcript cannot be empty")
        
        # Analyze and restructure the paragraph
        result = await analyze_paragraph_restructuring(request)
        
        return ParagraphRestructuringResponse(
            result=result,
            status="success"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.exception("Unexpected error in paragraph restructuring endpoint")
        return ParagraphRestructuringResponse(
            result=None,
            status="error",
            error=f"Internal error: {str(e)}"
        ) 