from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging
from app.services.question_retry_service import question_retry_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/retry/{submission_url:path}")
async def retry_failed_questions(submission_url: str) -> Dict[str, Any]:
    """
    Retry failed questions for a specific submission
    
    Args:
        submission_url: URL of the submission to retry
        
    Returns:
        Dict with retry results
    """
    try:
        logger.info(f"Manual retry requested for submission: {submission_url}")
        
        # Get current retry status
        status = question_retry_service.get_retry_status(submission_url)
        
        if status["total_retries"] == 0:
            return {
                "message": "No failed questions found for retry",
                "submission_url": submission_url,
                "retry_results": {
                    "retried": [],
                    "skipped": [],
                    "exhausted": [],
                    "successful": [],
                    "failed": []
                },
                "status": status
            }
        
        # Attempt retry
        retry_results = await question_retry_service.retry_failed_questions(submission_url)
        
        logger.info(f"Retry completed for submission {submission_url}: {retry_results}")
        
        return {
            "message": f"Retry completed for {len(retry_results['retried'])} questions",
            "submission_url": submission_url,
            "retry_results": retry_results,
            "status": question_retry_service.get_retry_status(submission_url)
        }
        
    except Exception as e:
        logger.error(f"Error during manual retry for submission {submission_url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Retry failed: {str(e)}")

@router.get("/status/{submission_url:path}")
async def get_retry_status(submission_url: str) -> Dict[str, Any]:
    """
    Get retry status for a specific submission
    
    Args:
        submission_url: URL of the submission to check
        
    Returns:
        Dict with retry status information
    """
    try:
        status = question_retry_service.get_retry_status(submission_url)
        
        return {
            "submission_url": submission_url,
            "status": status
        }
        
    except Exception as e:
        logger.error(f"Error getting retry status for submission {submission_url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")

@router.post("/cleanup")
async def cleanup_old_retries(max_age_hours: int = 24) -> Dict[str, str]:
    """
    Clean up old retry states
    
    Args:
        max_age_hours: Maximum age of retry states to keep (default 24 hours)
        
    Returns:
        Success message
    """
    try:
        question_retry_service.cleanup_old_retries(max_age_hours)
        
        return {
            "message": f"Cleaned up retry states older than {max_age_hours} hours",
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

@router.get("/health")
async def retry_service_health() -> Dict[str, Any]:
    """
    Health check for retry service
    
    Returns:
        Health status and basic statistics
    """
    try:
        total_retries = len(question_retry_service.retry_states)
        
        # Count by status
        pending_count = 0
        exhausted_count = 0
        
        for retry_state in question_retry_service.retry_states.values():
            if retry_state.should_retry():
                pending_count += 1
            elif retry_state.attempt_count >= retry_state.max_attempts:
                exhausted_count += 1
        
        return {
            "status": "healthy",
            "total_retry_states": total_retries,
            "pending_retries": pending_count,
            "exhausted_retries": exhausted_count,
            "service_ready": True
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "service_ready": False
        }