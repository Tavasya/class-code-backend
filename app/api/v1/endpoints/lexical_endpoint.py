from fastapi import APIRouter, HTTPException
from app.models.fluency_model import FluencyRequest, FluencyResponse, SimpleFluencyResponse
from app.services.fluency_service import analyze_fluency
import logging # It's good practice to have logging available

router = APIRouter()
logger = logging.getLogger(__name__) # Setup logger for the endpoint

@router.post("/analysis", response_model=SimpleFluencyResponse)
async def assess_fluency(request: FluencyRequest) -> SimpleFluencyResponse:
    """
    Assess speech fluency and coherence (simplified response)

    Args:
        request: FluencyRequest containing reference text and optionally word details / audio_duration

    Returns:
        SimpleFluencyResponse with grade, issues, wpm, cohesive device band level and feedback
    """
    try:
        full_response = await analyze_fluency(request)

        if full_response.status == "error":
            logger.error(f"Fluency analysis service returned an error: {full_response.error}")
            # If analyze_fluency itself had an error, we can return that in the simple response
            return SimpleFluencyResponse(
                grade=0,
                issues=[f"Analysis error: {full_response.error}"],
                wpm=0,
                cohesive_device_band_level=None,
                cohesive_device_feedback=None,
                status="error",
                error=full_response.error
            )
            # Or, re-raise an HTTPException if preferred for this direct endpoint
            # raise HTTPException(status_code=500, detail=full_response.error)

        return SimpleFluencyResponse(
            grade=full_response.fluency_metrics.overall_fluency_score,
            issues=full_response.key_findings,
            wpm=full_response.fluency_metrics.words_per_minute,
            cohesive_device_band_level=full_response.cohesive_device_band_level,
            cohesive_device_feedback=full_response.cohesive_device_feedback,
            status="success"
        )

    except Exception as e:
        # Handle unexpected errors during the endpoint call itself
        logger.exception("Unexpected error in assess_fluency endpoint") # Log the full exception
        return SimpleFluencyResponse(
            grade=0,
            issues=[f"Endpoint error: {str(e)}"], # Be cautious about exposing internal error details
            wpm=0,
            cohesive_device_band_level=None,
            cohesive_device_feedback=None,
            status="error",
            error=str(e) # Be cautious about exposing internal error details
        )
        # Or, re-raise an HTTPException
        # raise HTTPException(status_code=500, detail=f"Unexpected endpoint error: {str(e)}")
