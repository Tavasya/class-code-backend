import logging
from typing import Dict, Any
from fastapi import Request, HTTPException
from app.pubsub.utils import parse_pubsub_message
from app.services.practice_session_service import PracticeSessionService

logger = logging.getLogger(__name__)

class PracticeWebhook:
    """Webhook handler for practice pronunciation analysis results"""
    
    def __init__(self):
        self.practice_service = PracticeSessionService()
        logger.info("PracticeWebhook initialized")
    
    async def handle_practice_pronunciation_done_webhook(self, request: Request) -> Dict[str, str]:
        """
        Handle practice pronunciation analysis completion webhook
        
        This webhook receives pronunciation analysis results and updates
        the practice session accordingly:
        - Sentence analysis: Update sentence status, handle pass/fail
        - Word analysis: Update word status, advance to next word
        - Progress state machine: Move practice flow forward
        
        Args:
            request: FastAPI Request object containing Pub/Sub push message
            
        Returns:
            Success response
        """
        try:
            logger.info("🎯 Received practice pronunciation analysis webhook")
            
            # Parse the Pub/Sub message
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            # Extract key information
            practice_session_id = message_data.get("practice_session_id")
            webhook_session_id = message_data.get("webhook_session_id")
            analysis_type = message_data.get("analysis_type")  # "sentence" or "word"
            analysis_results = message_data.get("analysis_results", {})
            
            logger.info(f"📝 Practice session: {practice_session_id}")
            logger.info(f"🔍 Analysis type: {analysis_type}")
            logger.info(f"📊 Webhook session: {webhook_session_id}")
            
            if not practice_session_id:
                logger.error("❌ Missing practice_session_id in webhook")
                raise HTTPException(status_code=400, detail="Missing practice_session_id")
            
            # Route to appropriate handler based on analysis type
            if analysis_type == "sentence":
                await self._handle_sentence_analysis_result(
                    practice_session_id, webhook_session_id, analysis_results
                )
            elif analysis_type == "word":
                await self._handle_word_analysis_result(
                    practice_session_id, webhook_session_id, analysis_results
                )
            else:
                logger.warning(f"⚠️ Unknown analysis type: {analysis_type}")
                # Still return success to acknowledge webhook
            
            logger.info(f"✅ Practice pronunciation webhook processed successfully")
            return {"status": "success", "message": "Practice analysis processed"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"❌ Error processing practice pronunciation webhook")
            raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")
    
    async def _handle_sentence_analysis_result(self, 
                                             practice_session_id: str,
                                             webhook_session_id: str, 
                                             analysis_results: Dict[str, Any]) -> None:
        """
        Handle sentence pronunciation analysis results
        
        Args:
            practice_session_id: Practice session ID
            webhook_session_id: Webhook session ID
            analysis_results: Pronunciation analysis results
        """
        try:
            logger.info(f"🎤 Processing sentence analysis for session: {practice_session_id}")
            
            # Extract analysis data
            sentence_index = analysis_results.get("sentence_index", 0)
            pronunciation_score = analysis_results.get("pronunciation_score", 0)
            passed = analysis_results.get("passed", False)
            problematic_words = analysis_results.get("problematic_words", [])
            
            logger.info(f"📊 Sentence {sentence_index}: Score={pronunciation_score}, Passed={passed}")
            
            # Get current session
            session = self.practice_service.get_practice_session(practice_session_id)
            if not session:
                logger.error(f"❌ Practice session not found: {practice_session_id}")
                return
            
            sentences = session.get('sentences', [])
            if not (0 <= sentence_index < len(sentences)):
                logger.error(f"❌ Invalid sentence index: {sentence_index}")
                return
            
            # Update sentence with analysis results
            sentences[sentence_index].update({
                'attempts': sentences[sentence_index].get('attempts', 0) + 1,
                'best_score': max(sentences[sentence_index].get('best_score', 0), pronunciation_score),
                'last_score': pronunciation_score,
                'completed': True,
                'passed': passed
            })
            
            if passed:
                logger.info(f"✅ Sentence {sentence_index} passed! Moving to next sentence")
                
                # Move to next sentence or complete practice
                success = self.practice_service.advance_practice_progress(
                    session_id=practice_session_id,
                    passed=True
                )
                
                if success:
                    logger.info(f"🎯 Advanced to next sentence successfully")
                else:
                    logger.error(f"❌ Failed to advance practice progress")
            else:
                logger.info(f"❌ Sentence {sentence_index} failed. Setting up word practice")
                
                # Create problematic words for practice
                word_practice_list = []
                current_sentence = sentences[sentence_index]
                sentence_text = current_sentence.get('text', '')
                
                for word_info in problematic_words:
                    word_practice_list.append({
                        'word': word_info.get('word', ''),
                        'sentence_index': sentence_index,
                        'sentence_context': sentence_text,
                        'difficulty_score': word_info.get('difficulty_score', 50),
                        'completed': False,
                        'passed': False,
                        'attempts': 0,
                        'best_score': 0
                    })
                
                # Update session with problematic words and transition to word practice
                update_success = self.practice_service.update_practice_session(
                    session_id=practice_session_id,
                    sentences=sentences,
                    problematic_words=word_practice_list,
                    status="practicing_words",
                    current_word_index=0
                )
                
                if update_success:
                    logger.info(f"🎯 Transitioned to word practice with {len(word_practice_list)} words")
                else:
                    logger.error(f"❌ Failed to transition to word practice")
            
        except Exception as e:
            logger.error(f"❌ Error handling sentence analysis result: {str(e)}")
    
    async def _handle_word_analysis_result(self, 
                                         practice_session_id: str,
                                         webhook_session_id: str,
                                         analysis_results: Dict[str, Any]) -> None:
        """
        Handle word pronunciation analysis results
        
        Args:
            practice_session_id: Practice session ID
            webhook_session_id: Webhook session ID
            analysis_results: Pronunciation analysis results
        """
        try:
            logger.info(f"🔤 Processing word analysis for session: {practice_session_id}")
            
            # Extract analysis data
            word = analysis_results.get("word", "")
            pronunciation_score = analysis_results.get("pronunciation_score", 0)
            passed = analysis_results.get("passed", False)
            
            logger.info(f"📊 Word '{word}': Score={pronunciation_score}, Passed={passed}")
            
            # Get current session
            session = self.practice_service.get_practice_session(practice_session_id)
            if not session:
                logger.error(f"❌ Practice session not found: {practice_session_id}")
                return
            
            current_word_index = session.get('current_word_index', 0)
            problematic_words = session.get('problematic_words', [])
            
            if not (0 <= current_word_index < len(problematic_words)):
                logger.error(f"❌ Invalid word index: {current_word_index}")
                return
            
            # Update word with analysis results
            problematic_words[current_word_index].update({
                'attempts': problematic_words[current_word_index].get('attempts', 0) + 1,
                'best_score': max(problematic_words[current_word_index].get('best_score', 0), pronunciation_score),
                'last_score': pronunciation_score,
                'completed': True,
                'passed': passed
            })
            
            # Advance word practice progress
            success = self.practice_service.advance_practice_progress(
                session_id=practice_session_id,
                passed=passed
            )
            
            if success:
                if passed:
                    logger.info(f"✅ Word '{word}' passed! Moving to next word or back to sentence")
                else:
                    logger.info(f"❌ Word '{word}' failed. Will retry or continue to next word")
            else:
                logger.error(f"❌ Failed to advance word practice progress")
            
        except Exception as e:
            logger.error(f"❌ Error handling word analysis result: {str(e)}")