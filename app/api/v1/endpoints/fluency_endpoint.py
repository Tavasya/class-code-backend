from fastapi import APIRouter, HTTPException
from app.models.fluency_model import FluencyRequest, FluencyResponse, SimpleFluencyResponse
from app.services.fluency_service import analyze_fluency

router = APIRouter()

@router.post("/analysis", response_model=SimpleFluencyResponse)
async def assess_fluency(request: FluencyRequest) -> SimpleFluencyResponse:
    """
    Assess speech fluency and coherence (simplified response)
    
    Args:
        request: FluencyRequest containing reference text and optionally word details / audio_duration
        
    Returns:
        SimpleFluencyResponse with grade, issues, and wpm
    """
    try:
        full_response = await analyze_fluency(request)
        
        if full_response.status == "error":
            # If analyze_fluency itself had an error, we can return that in the simple response
            return SimpleFluencyResponse(
                grade=0,
                issues=[f"Analysis error: {full_response.error}"],
                wpm=0,
                status="error",
                error=full_response.error
            )
            # Or, re-raise an HTTPException if preferred for this direct endpoint
            # raise HTTPException(status_code=500, detail=full_response.error)

        return SimpleFluencyResponse(
            grade=full_response.fluency_metrics.overall_fluency_score,
            issues=full_response.key_findings,
            wpm=full_response.fluency_metrics.words_per_minute,
            status="success"
        )
        
    except Exception as e:
        # Handle unexpected errors during the endpoint call itself
        # You might want to log the exception e here
        return SimpleFluencyResponse(
            grade=0,
            issues=[f"Endpoint error: {str(e)}"],
            wpm=0,
            status="error",
            error=str(e)
        )
        # Or, re-raise an HTTPException
        # raise HTTPException(status_code=500, detail=f"Unexpected endpoint error: {str(e)}")
