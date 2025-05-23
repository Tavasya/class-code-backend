"""
Simple in-memory results store for testing purposes
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ResultsStore:
    """Simple in-memory store for analysis results"""
    
    def __init__(self):
        self._results: Dict[str, Dict[str, Any]] = {}
    
    def store_result(self, submission_url: str, results: Dict[str, Any]) -> None:
        """Store analysis results for a submission"""
        self._results[submission_url] = {
            **results,
            "stored_at": datetime.now().isoformat()
        }
        logger.info(f"Stored results for submission: {submission_url}")
    
    def get_result(self, submission_url: str) -> Optional[Dict[str, Any]]:
        """Get analysis results for a submission"""
        return self._results.get(submission_url)
    
    def has_result(self, submission_url: str) -> bool:
        """Check if results exist for a submission"""
        return submission_url in self._results
    
    def clear_result(self, submission_url: str) -> None:
        """Clear results for a submission"""
        if submission_url in self._results:
            del self._results[submission_url]
            logger.info(f"Cleared results for submission: {submission_url}")
    
    def list_all_submissions(self) -> list:
        """List all submissions with results"""
        return list(self._results.keys())

# Global instance
results_store = ResultsStore() 