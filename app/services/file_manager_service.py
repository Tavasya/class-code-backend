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
        timestamp = datetime.now().timestamp()
        unique_id = str(uuid.uuid4())[:8]  # Use UUID for uniqueness
        return f"session_{hash(submission_url)}_{question_number}_{int(timestamp)}_{unique_id}"
    
    async def register_file_session(
        self, 
        session_id: str, 
        file_path: str, 
        dependent_services: Set[str],
        cleanup_timeout_minutes: int = 60,
        metadata: Optional[Dict] = None
    ) -> None:
        """Register a file session with its dependencies"""
        async with self._lock:
            self._file_sessions[session_id] = {
                "file_path": file_path,
                "created_at": datetime.now(),
                "cleanup_timeout": datetime.now() + timedelta(minutes=cleanup_timeout_minutes),
                "cleanup_completed": False,
                "metadata": metadata or {}
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
            else:
                logger.info(f"Service {service_name} was not in dependencies for session {session_id} (already completed or not required)")
            
            # Check if all services are complete
            if not dependencies:
                logger.info(f"All services completed for session {session_id}. Scheduling cleanup with delay.")
                # Add delay to ensure all services finish their cleanup
                asyncio.create_task(self._delayed_cleanup(session_id))
                return True
            
            return False
    
    async def _delayed_cleanup(self, session_id: str, delay_seconds: float = 120.0) -> None:
        """Clean up session after a delay to ensure all services complete"""
        logger.info(f"⏰ Scheduled cleanup for session {session_id} in {delay_seconds} seconds")
        await asyncio.sleep(delay_seconds)
        logger.info(f"⏰ Cleanup delay expired for session {session_id}, starting cleanup")
        async with self._lock:
            await self._cleanup_file_session(session_id)
    
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
        logger.info(f"🧹 Starting cleanup for session {session_id}, file: {file_path}")
        
        try:
            files_cleaned = 0
            
            # Clean up original file
            if os.path.exists(file_path):
                file_size_mb = os.path.getsize(file_path) / 1024 / 1024
                os.unlink(file_path)
                files_cleaned += 1
                logger.info(f"🗑️ Cleaned up original file: {file_path} ({file_size_mb:.2f}MB)")
            else:
                logger.warning(f"⚠️ Original file not found during cleanup: {file_path}")
                
            # Also clean up related WAV file if exists
            wav_file = os.path.splitext(file_path)[0] + '.wav'
            if os.path.exists(wav_file):
                wav_size_mb = os.path.getsize(wav_file) / 1024 / 1024
                os.unlink(wav_file)
                files_cleaned += 1
                logger.info(f"🗑️ Cleaned up WAV file: {wav_file} ({wav_size_mb:.2f}MB)")
            
            logger.info(f"✅ Session {session_id} cleanup completed - {files_cleaned} files removed")
            session_info["cleanup_completed"] = True
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup session {session_id}, file {file_path}: {str(e)}")
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
    
    async def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get information about a file session"""
        async with self._lock:
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