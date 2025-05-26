from fastapi import APIRouter, HTTPException
from app.services.file_manager_service import file_manager
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/file-sessions")
async def get_active_file_sessions() -> Dict[str, Any]:
    """Get all active file sessions for debugging"""
    try:
        active_sessions = file_manager.get_active_sessions()
        return {
            "status": "success",
            "active_sessions": active_sessions,
            "total_active": len(active_sessions)
        }
    except Exception as e:
        logger.error(f"Error getting file sessions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting file sessions: {str(e)}")

@router.post("/cleanup-session/{session_id}")
async def force_cleanup_session(session_id: str) -> Dict[str, str]:
    """Force cleanup of a specific session (for debugging/emergency)"""
    try:
        session_info = file_manager.get_session_info(session_id)
        if not session_info:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        await file_manager.force_cleanup_session(session_id)
        
        return {
            "status": "success",
            "message": f"Forced cleanup of session {session_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error cleaning up session: {str(e)}")

@router.post("/periodic-cleanup")
async def trigger_periodic_cleanup() -> Dict[str, str]:
    """Manually trigger periodic cleanup (for debugging)"""
    try:
        await file_manager.periodic_cleanup()
        return {
            "status": "success",
            "message": "Periodic cleanup completed"
        }
    except Exception as e:
        logger.error(f"Error in manual periodic cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in periodic cleanup: {str(e)}") 