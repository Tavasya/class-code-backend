from fastapi import APIRouter, HTTPException
from app.models.fluency_model import FluencyRequest, FluencyResponse
from app.services.fluency_service import analyze_fluency

router = APIRouter()

@router.post("/analysis", response_model=FluencyResponse)
async def assess_fluency(request: FluencyRequest) -> FluencyResponse:
    """
    Assess speech fluency and coherence
    
    Args:
        request: FluencyRequest containing reference text and word details
        
    Returns:
        FluencyResponse with analysis results
    """
    try:
        response = await analyze_fluency(request)
        if response.status == "error":
            raise HTTPException(status_code=500, detail=response.error)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
