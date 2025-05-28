import os
import uuid
import logging
import asyncio
import tempfile
from typing import Dict, Set, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class FileManagerService:
    """Centralized file lifecycle management service"""
    
    def __init__(self):
        # Track file sessions: session_id -> file info
        self._file_sessions: Dict[str, Dict] = {}
        # Track file dependencies: session_id -> set of services that need the file
        self._file_dependencies: Dict[str, Set[str]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    def generate_session_id(self, submission_url: str, question_number: int) -> str:
        """Generate a unique session ID for file tracking"""
        timestamp = int(datetime.now().timestamp())
        unique_id = uuid.uuid4().hex[:8]  # 8-character unique identifier
        return f"session_{hash(submission_url)}_{question_number}_{timestamp}_{unique_id}"
    
    async def register_file_session(
        self, 
        session_id: str, 
        file_path: str, 
        dependent_services: Set[str],
        cleanup_timeout_minutes: int = 60
    ) -> None:
        """Register a file session with its dependencies"""
        async with self._lock:
            self._file_sessions[session_id] = {
                "file_path": file_path,
                "created_at": datetime.now(),
                "cleanup_timeout": datetime.now() + timedelta(minutes=cleanup_timeout_minutes),
                "cleanup_completed": False
            }
            self._file_dependencies[session_id] = dependent_services.copy()
            
        logger.info(f"Registered file session {session_id} with dependencies: {dependent_services}")
    
    async def mark_service_complete(self, session_id: str, service_name: str) -> bool:
        """Mark a service as complete for a file session. Returns True if all services are done."""
        async with self._lock:
            if session_id not in self._file_dependencies:
                logger.warning(f"Session {session_id} not found for service completion: {service_name}")
                return False
            
            dependencies = self._file_dependencies[session_id]
            if service_name in dependencies:
                dependencies.remove(service_name)
                logger.info(f"Service {service_name} completed for session {session_id}. Remaining: {dependencies}")
            
            # Check if all services are complete
            if not dependencies:
                logger.info(f"All services completed for session {session_id}. Ready for cleanup.")
                await self._cleanup_file_session(session_id)
                return True
            
            return False
    
    async def _cleanup_file_session(self, session_id: str) -> None:
        """Clean up files for a completed session"""
        if session_id not in self._file_sessions:
            logger.warning(f"Cannot cleanup session {session_id}: not found")
            return
        
        session_info = self._file_sessions[session_id]
        if session_info["cleanup_completed"]:
            logger.info(f"Session {session_id} already cleaned up")
            return
        
        file_path = session_info["file_path"]
        
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
                logger.info(f"Successfully cleaned up file: {file_path}")
            else:
                logger.warning(f"File not found during cleanup: {file_path}")
            
            session_info["cleanup_completed"] = True
            
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path} for session {session_id}: {str(e)}")
            # Don't raise - we'll retry with periodic cleanup
    
    async def force_cleanup_session(self, session_id: str) -> None:
        """Force cleanup of a session (for error scenarios)"""
        async with self._lock:
            await self._cleanup_file_session(session_id)
            # Remove from tracking
            self._file_sessions.pop(session_id, None)
            self._file_dependencies.pop(session_id, None)
    
    async def periodic_cleanup(self) -> None:
        """Clean up orphaned files and expired sessions"""
        current_time = datetime.now()
        sessions_to_cleanup = []
        
        async with self._lock:
            for session_id, session_info in self._file_sessions.items():
                # Clean up expired sessions
                if current_time > session_info["cleanup_timeout"]:
                    logger.warning(f"Session {session_id} expired, forcing cleanup")
                    sessions_to_cleanup.append(session_id)
        
        # Clean up expired sessions
        for session_id in sessions_to_cleanup:
            await self.force_cleanup_session(session_id)
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get information about a file session"""
        return self._file_sessions.get(session_id)
    
    def get_active_sessions(self) -> Dict[str, Dict]:
        """Get all active file sessions (for debugging/monitoring)"""
        return {
            session_id: {
                "file_path": info["file_path"],
                "created_at": info["created_at"].isoformat(),
                "dependencies": list(self._file_dependencies.get(session_id, set())),
                "cleanup_completed": info["cleanup_completed"]
            }
            for session_id, info in self._file_sessions.items()
            if not info["cleanup_completed"]
        }

# Global instance
file_manager = FileManagerService() 