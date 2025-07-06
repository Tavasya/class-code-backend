from app.core.config import supabase
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class PracticeSessionService:
    def __init__(self):
        self.supabase = supabase
        logger.info("PracticeSessionService initialized")

    def create_practice_session(self, 
                               transcript: Optional[str] = None,
                               improved_transcript: Optional[str] = None,
                               audio_url: Optional[str] = None) -> Optional[str]:
        """
        Create a new practice session record
        
        Args:
            transcript: Original transcript text
            improved_transcript: Improved transcript text
            audio_url: Audio URL if provided
            
        Returns:
            Practice session ID if successful, None otherwise
        """
        operation = "CREATE_PRACTICE_SESSION"
        
        try:
            # Generate a unique ID for the practice session
            session_id = str(uuid.uuid4())
            
            # Prepare the data to insert
            session_data = {
                "id": session_id,
                "original_transcript": transcript,
                "improved_transcript": improved_transcript,
                "original_audio_url": audio_url,
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"🚀 Creating practice session with ID: {session_id}")
            logger.info(f"📝 Session data: transcript={bool(transcript)}, improved_transcript={bool(improved_transcript)}, audio_url={bool(audio_url)}")
            
            # Insert into practice_sessions table
            result = self.supabase.table('practice_sessions').insert(session_data).execute()
            
            if result.data and len(result.data) > 0:
                created_session = result.data[0]
                logger.info(f"✅ Practice session created successfully: {created_session['id']}")
                return created_session['id']
            else:
                error_msg = getattr(result, 'error', 'No data returned from insert operation')
                logger.error(f"❌ Failed to create practice session: {error_msg}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error creating practice session: {str(e)}")
            return None

    def get_practice_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a practice session by ID
        
        Args:
            session_id: Practice session ID
            
        Returns:
            Practice session data if found, None otherwise
        """
        try:
            result = self.supabase.table('practice_sessions').select('*').eq('id', session_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching practice session {session_id}: {str(e)}")
            return None

    def list_practice_sessions(self, limit: int = 50) -> list:
        """
        List recent practice sessions
        
        Args:
            limit: Maximum number of sessions to return
            
        Returns:
            List of practice sessions
        """
        try:
            result = self.supabase.table('practice_sessions').select('*').order('created_at', desc=True).limit(limit).execute()
            
            if result.data:
                return result.data
            return []
            
        except Exception as e:
            logger.error(f"❌ Error listing practice sessions: {str(e)}")
            return []

    def update_practice_session(self, session_id: str, **updates) -> bool:
        """
        Update a practice session with new data
        
        Args:
            session_id: Practice session ID
            **updates: Fields to update
            
        Returns:
            True if successful, False otherwise
        """
        operation = "UPDATE_PRACTICE_SESSION"
        
        try:
            # Check if session exists
            session = self.get_practice_session(session_id)
            if not session:
                logger.error(f"❌ Practice session not found: {session_id}")
                return False
            
            logger.info(f"🔄 Updating practice session {session_id} with fields: {list(updates.keys())}")
            
            # Update the session
            result = self.supabase.table('practice_sessions').update(updates).eq('id', session_id).execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"✅ Successfully updated practice session: {session_id}")
                return True
            else:
                error_msg = getattr(result, 'error', 'No data returned from update operation')
                logger.error(f"❌ Failed to update practice session {session_id}: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error updating practice session {session_id}: {str(e)}")
            return False