from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.core.results_store import results_store
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/submission/{submission_url}")
async def get_submission_results(submission_url: str) -> List[Dict[str, Any]]:
    """Get analysis results for a submission in the new standardized format"""
    
    # Try to get the transformed results first
    transformed_results = results_store.get_result_transformed(submission_url)
    
    if transformed_results is not None:
        return transformed_results
    
    # If no results found, raise 404
    raise HTTPException(
        status_code=404, 
        detail=f"No results found for submission: {submission_url}"
    )

@router.get("/submission/{submission_url}/raw")
async def get_submission_results_raw(submission_url: str) -> Dict[str, Any]:
    """Get raw analysis results for a submission (for debugging)"""
    
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