import logging
from typing import Dict, Any
from fastapi import Request, HTTPException
from app.pubsub.client import PubSubClient
from app.pubsub.utils import parse_pubsub_message
from app.services.analysis_coordinator_service import AnalysisCoordinatorService
from app.services.fluency_service import get_fluency_coherence_analysis
from app.services.grammar_service import analyze_grammar
from app.services.lexical_service import analyze_lexical_resources
from app.services.pronunciation_service import PronunciationService
from app.models.analysis_model import AudioDoneMessage, TranscriptionDoneMessage, QuestionAnalysisReadyMessage

logger = logging.getLogger(__name__)

class AnalysisWebhook:
    """Webhook handler for analysis-related messages from Pub/Sub push"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        self.analysis_coordinator = AnalysisCoordinatorService()
        
    async def handle_audio_conversion_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle audio conversion completed webhook from Pub/Sub push"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            # Create AudioDoneMessage
            audio_message = AudioDoneMessage(
                wav_path=message_data["wav_path"],
                question_number=message_data["question_number"],
                submission_url=message_data["submission_url"],
                original_audio_url=message_data["original_audio_url"]
            )
            
            # Handle in coordinator
            await self.analysis_coordinator.handle_audio_done(audio_message)
            
            logger.info(f"Successfully handled audio conversion done for question {audio_message.question_number}")
            return {"status": "success", "message": "Audio conversion done processed"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling audio conversion done webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def handle_transcription_done_webhook(self, request: Request) -> Dict[str, str]:
        """Handle transcription completed webhook from Pub/Sub push"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            # Create TranscriptionDoneMessage
            transcription_message = TranscriptionDoneMessage(
                text=message_data["text"],
                error=message_data.get("error"),
                question_number=message_data["question_number"],
                submission_url=message_data["submission_url"],
                audio_url=message_data["audio_url"]
            )
            
            # Handle in coordinator
            await self.analysis_coordinator.handle_transcription_done(transcription_message)
            
            logger.info(f"Successfully handled transcription done for question {transcription_message.question_number}")
            return {"status": "success", "message": "Transcription done processed"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling transcription done webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def handle_question_analysis_ready_webhook(self, request: Request) -> Dict[str, str]:
        """Handle question ready for analysis webhook from Pub/Sub push"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            wav_path = message_data["wav_path"]
            transcript = message_data["transcript"]
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            audio_url = message_data["audio_url"]
            
            logger.info(f"Starting analysis for question {question_number}")
            
            # Run all analysis services in parallel
            analysis_results = {}
            
            # 1. Pronunciation Analysis
            try:
                pronunciation_result = await PronunciationService.analyze_pronunciation(wav_path, transcript)
                analysis_results["pronunciation"] = pronunciation_result
                
                # Publish pronunciation done
                self.pubsub_client.publish_message_by_name(
                    "PRONOUN_DONE",
                    {
                        "question_number": question_number,
                        "submission_url": submission_url,
                        "result": pronunciation_result
                    }
                )
            except Exception as e:
                logger.error(f"Pronunciation analysis failed: {str(e)}")
                analysis_results["pronunciation"] = {"error": str(e)}
            
            # 2. Grammar Analysis
            try:
                grammar_result = await analyze_grammar(transcript)
                analysis_results["grammar"] = grammar_result
                
                # Publish grammar done
                self.pubsub_client.publish_message_by_name(
                    "GRAMMER_DONE",
                    {
                        "question_number": question_number,
                        "submission_url": submission_url,
                        "result": grammar_result
                    }
                )
            except Exception as e:
                logger.error(f"Grammar analysis failed: {str(e)}")
                analysis_results["grammar"] = {"error": str(e)}
            
            # 3. Lexical Analysis
            try:
                sentences = [s.strip() for s in transcript.split('.') if s.strip()]
                lexical_result = await analyze_lexical_resources(sentences)
                analysis_results["lexical"] = lexical_result
                
                # Publish lexical done
                self.pubsub_client.publish_message_by_name(
                    "LEXICAL_DONE",
                    {
                        "question_number": question_number,
                        "submission_url": submission_url,
                        "result": [feedback.dict() for feedback in lexical_result]
                    }
                )
            except Exception as e:
                logger.error(f"Lexical analysis failed: {str(e)}")
                analysis_results["lexical"] = {"error": str(e)}
            
            # 4. Fluency Analysis
            try:
                # Get word details from pronunciation if available
                word_details = analysis_results.get("pronunciation", {}).get("word_details", [])
                fluency_result = await get_fluency_coherence_analysis(transcript, word_details)
                analysis_results["fluency"] = fluency_result
                
                # Publish fluency done
                self.pubsub_client.publish_message_by_name(
                    "FLUENCY_DONE",
                    {
                        "question_number": question_number,
                        "submission_url": submission_url,
                        "result": fluency_result
                    }
                )
            except Exception as e:
                logger.error(f"Fluency analysis failed: {str(e)}")
                analysis_results["fluency"] = {"error": str(e)}
            
            # Publish analysis complete
            self.pubsub_client.publish_message_by_name(
                "ANALYSIS_COMPLETE",
                {
                    "question_number": question_number,
                    "submission_url": submission_url,
                    "analysis_results": analysis_results
                }
            )
            
            logger.info(f"Successfully completed all analysis for question {question_number}")
            return {"status": "success", "message": "Question analysis completed"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling question analysis ready webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
    
    async def handle_analysis_complete_webhook(self, request: Request) -> Dict[str, str]:
        """Handle analysis completion webhook from Pub/Sub push"""
        try:
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            question_number = message_data["question_number"]
            submission_url = message_data["submission_url"]
            analysis_results = message_data["analysis_results"]
            
            # Here you could store final results, send notifications, etc.
            logger.info(f"Analysis completed for question {question_number} in submission {submission_url}")
            
            # TODO: Implement final result storage/notification logic here
            # For example: store to database, send notification to frontend, etc.
            
            return {"status": "success", "message": "Analysis completion processed"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling analysis complete webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") 