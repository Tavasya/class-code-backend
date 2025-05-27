from fastapi import APIRouter, Depends, Request
from app.models.submission_model import SubmissionRequest, SubmissionResponse
from app.services.submission_service import SubmissionService
import base64
import json

router = APIRouter()

def get_submission_service():
    return SubmissionService()

@router.post("/submit", response_model=SubmissionResponse)
async def submit_audio(
    request: Request,
    submission_service: SubmissionService = Depends(get_submission_service)
) -> SubmissionResponse:
    """
    Endpoint to receive audio URLs and submission URL from the frontend or Pub/Sub push.
    """
    body = await request.json()
    # Check if this is a Pub/Sub push message
    if "message" in body and "data" in body["message"]:
        # Decode base64 data
        decoded_data = base64.b64decode(body["message"]["data"]).decode("utf-8")
        data = json.loads(decoded_data)
        submission_request = SubmissionRequest(**data)
    else:
        # Assume it's a direct frontend request
        submission_request = SubmissionRequest(**body)
    return await submission_service.process_submission(submission_request) 
#test