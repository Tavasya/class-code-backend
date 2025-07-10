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
                               audio_url: Optional[str] = None) -> Optional[str]:
        """
        Create a new practice session record
        
        Args:
            transcript: Transcript text for practice
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
                "original_audio_url": audio_url,
                "created_at": datetime.now().isoformat()
            }
            
            logger.info(f"🚀 Creating practice session with ID: {session_id}")
            logger.info(f"📝 Session data: transcript={bool(transcript)}, audio_url={bool(audio_url)}")
            
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

    def get_current_practice_content(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current practice content (sentence or word) based on session state
        
        Args:
            session_id: Practice session ID
            
        Returns:
            Current practice content or None if not found
        """
        try:
            session = self.get_practice_session(session_id)
            if not session:
                logger.error(f"❌ Session not found: {session_id}")
                return None
            
            status = session.get('status')
            sentences = session.get('sentences', [])
            current_sentence_index = session.get('current_sentence_index', 0)
            current_word_index = session.get('current_word_index', 0)
            
            if status == 'practicing_sentences':
                # Return current sentence for practice
                if 0 <= current_sentence_index < len(sentences):
                    return {
                        "type": "sentence",
                        "content": sentences[current_sentence_index],
                        "index": current_sentence_index,
                        "total": len(sentences)
                    }
            elif status == 'practicing_words':
                # Return current word for practice
                problematic_words = session.get('problematic_words', [])
                if 0 <= current_word_index < len(problematic_words):
                    return {
                        "type": "word",
                        "content": problematic_words[current_word_index],
                        "index": current_word_index,
                        "total": len(problematic_words)
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting current practice content for session {session_id}: {str(e)}")
            return None

    def advance_practice_progress(self, session_id: str, passed: bool = False) -> bool:
        """
        Advance practice progress to next sentence or word
        
        Args:
            session_id: Practice session ID
            passed: Whether current content was passed
            
        Returns:
            True if advanced successfully, False otherwise
        """
        try:
            session = self.get_practice_session(session_id)
            if not session:
                logger.error(f"❌ Session not found: {session_id}")
                return False
            
            status = session.get('status')
            current_sentence_index = session.get('current_sentence_index', 0)
            current_word_index = session.get('current_word_index', 0)
            sentences = session.get('sentences', [])
            
            if status == 'practicing_sentences':
                if passed:
                    # Mark current sentence as passed and move to next
                    if 0 <= current_sentence_index < len(sentences):
                        sentences[current_sentence_index]['passed'] = True
                        sentences[current_sentence_index]['completed'] = True
                    
                    # Move to next sentence or complete practice
                    next_sentence_index = current_sentence_index + 1
                    if next_sentence_index < len(sentences):
                        return self.update_practice_session(
                            session_id=session_id,
                            sentences=sentences,
                            current_sentence_index=next_sentence_index
                        )
                    else:
                        # All sentences completed
                        return self.update_practice_session(
                            session_id=session_id,
                            sentences=sentences,
                            status="completed"
                        )
                else:
                    # Current sentence failed, need to practice words
                    # This would typically involve identifying problematic words
                    # For now, just mark as needs word practice
                    return self.update_practice_session(
                        session_id=session_id,
                        sentences=sentences,
                        status="practicing_words",
                        current_word_index=0
                    )
            
            elif status == 'practicing_words':
                problematic_words = session.get('problematic_words', [])
                if passed:
                    # Mark current word as passed and move to next
                    if 0 <= current_word_index < len(problematic_words):
                        problematic_words[current_word_index]['passed'] = True
                        problematic_words[current_word_index]['completed'] = True
                    
                    # Move to next word or back to sentence practice
                    next_word_index = current_word_index + 1
                    if next_word_index < len(problematic_words):
                        return self.update_practice_session(
                            session_id=session_id,
                            problematic_words=problematic_words,
                            current_word_index=next_word_index
                        )
                    else:
                        # All words completed, return to sentence practice
                        return self.update_practice_session(
                            session_id=session_id,
                            problematic_words=problematic_words,
                            status="practicing_sentences"
                        )
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error advancing practice progress for session {session_id}: {str(e)}")
            return False

    def get_practice_progress(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed practice progress information
        
        Args:
            session_id: Practice session ID
            
        Returns:
            Practice progress information or None if not found
        """
        try:
            session = self.get_practice_session(session_id)
            if not session:
                return None
            
            status = session.get('status')
            sentences = session.get('sentences', [])
            current_sentence_index = session.get('current_sentence_index', 0)
            current_word_index = session.get('current_word_index', 0)
            problematic_words = session.get('problematic_words', [])
            
            # Calculate progress metrics
            sentences_completed = sum(1 for s in sentences if s.get('completed', False))
            sentences_passed = sum(1 for s in sentences if s.get('passed', False))
            words_completed = sum(1 for w in problematic_words if w.get('completed', False))
            words_passed = sum(1 for w in problematic_words if w.get('passed', False))
            
            return {
                "session_id": session_id,
                "status": status,
                "current_sentence_index": current_sentence_index,
                "current_word_index": current_word_index,
                "sentences": {
                    "total": len(sentences),
                    "completed": sentences_completed,
                    "passed": sentences_passed,
                    "current": current_sentence_index
                },
                "words": {
                    "total": len(problematic_words),
                    "completed": words_completed,
                    "passed": words_passed,
                    "current": current_word_index
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting practice progress for session {session_id}: {str(e)}")
            return None