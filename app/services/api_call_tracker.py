import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class APICallTracker:
    """Centralized API call tracking service"""
    
    def __init__(self):
        # Track calls per submission: submission_url -> call counts
        self._submission_calls: Dict[str, Dict[str, int]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def increment_openai_call(self, submission_url: str, service_name: str, question_number: Optional[int] = None) -> int:
        """
        Increment OpenAI API call count for a submission
        
        Args:
            submission_url: The submission URL
            service_name: Name of the service making the call (grammar, vocabulary, etc.)
            question_number: Optional question number for granular tracking
            
        Returns:
            Current total OpenAI calls for this submission
        """
        async with self._lock:
            if submission_url not in self._submission_calls:
                self._submission_calls[submission_url] = {
                    "total_openai_calls": 0,
                    "grammar_calls": 0,
                    "vocabulary_calls": 0,
                    "pronunciation_calls": 0,
                    "fluency_calls": 0,
                    "lexical_calls": 0,
                    "paragraph_restructuring_calls": 0,
                    "last_updated": datetime.now().isoformat()
                }
            
            # Increment service-specific counter
            service_key = f"{service_name}_calls"
            if service_key in self._submission_calls[submission_url]:
                self._submission_calls[submission_url][service_key] += 1
            
            # Increment total counter
            self._submission_calls[submission_url]["total_openai_calls"] += 1
            self._submission_calls[submission_url]["last_updated"] = datetime.now().isoformat()
            
            total_calls = self._submission_calls[submission_url]["total_openai_calls"]
            
            logger.info(f"🔢 OpenAI API call #{total_calls} for {service_name} - Submission: {submission_url}")
            
            if question_number:
                logger.info(f"📝 Question {question_number} - {service_name} call recorded")
            
            return total_calls
    
    async def get_submission_call_counts(self, submission_url: str) -> Dict[str, int]:
        """Get all call counts for a submission"""
        async with self._lock:
            return self._submission_calls.get(submission_url, {
                "total_openai_calls": 0,
                "grammar_calls": 0,
                "vocabulary_calls": 0,
                "pronunciation_calls": 0,
                "fluency_calls": 0,
                "lexical_calls": 0,
                "paragraph_restructuring_calls": 0
            })
    
    async def cleanup_submission(self, submission_url: str) -> None:
        """Clean up tracking data for a completed submission"""
        async with self._lock:
            if submission_url in self._submission_calls:
                final_counts = self._submission_calls[submission_url]
                logger.info(f"🧹 Cleaning up API call tracking for {submission_url}. Final counts: {final_counts}")
                del self._submission_calls[submission_url]
    
    async def get_all_active_submissions(self) -> Dict[str, Dict[str, int]]:
        """Get call counts for all active submissions (for debugging/monitoring)"""
        async with self._lock:
            return self._submission_calls.copy()

# Global instance
api_call_tracker = APICallTracker()