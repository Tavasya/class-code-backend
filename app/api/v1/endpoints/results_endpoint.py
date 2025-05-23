from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.core.results_store import results_store
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/submission/{submission_url}")
async def get_submission_results(submission_url: str) -> Dict[str, Any]:
    """Get analysis results for a submission (for testing)"""
    
    results = results_store.get_result(submission_url)
    
    if not results:
        raise HTTPException(
            status_code=404, 
            detail=f"No results found for submission: {submission_url}"
        )
    
    return results

@router.get("/submissions")
async def list_all_submissions() -> Dict[str, Any]:
    """List all submissions with results (for testing)"""
    
    submissions = results_store.list_all_submissions()
    
    return {
        "submissions": submissions,
        "count": len(submissions)
    }

@router.delete("/submission/{submission_url}")
async def clear_submission_results(submission_url: str) -> Dict[str, str]:
    """Clear results for a submission (for testing)"""
    
    if not results_store.has_result(submission_url):
        raise HTTPException(
            status_code=404, 
            detail=f"No results found for submission: {submission_url}"
        )
    
    results_store.clear_result(submission_url)
    
    return {"message": f"Results cleared for submission: {submission_url}"} 