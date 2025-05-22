from fastapi import APIRouter, Depends
from app.models.submission_model import SubmissionRequest, SubmissionResponse
from app.services.submission_service import SubmissionService

router = APIRouter()

def get_submission_service():
    return SubmissionService()

@router.post("/submit", response_model=SubmissionResponse)
async def submit_audio(
    request: SubmissionRequest,
    submission_service: SubmissionService = Depends(get_submission_service)
) -> SubmissionResponse:
    """
    Endpoint to receive audio URLs and submission URL from the frontend
    """
    return await submission_service.process_submission(request) 