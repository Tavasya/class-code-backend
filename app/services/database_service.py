from app.core.config import supabase, SUPABASE_URL
import logging
from typing import List, Dict, Any, Optional
import json

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.supabase = supabase
        self.supabase_url = SUPABASE_URL
        # Extract project reference from URL (e.g., "drcsbokflpzbhuzsksws" from the URL)
        self.supabase_project = SUPABASE_URL.split("//")[1].split(".")[0] if SUPABASE_URL else "unknown"
        
        logger.info(f"DatabaseService initialized with Supabase instance: {self.supabase_project} ({self.supabase_url})")

    def _log_operation_start(self, operation: str, submission_url: str = None, **kwargs):
        """Log the start of a database operation with full context"""
        context = f"Supabase Project: {self.supabase_project} | URL: {self.supabase_url}"
        if submission_url:
            context += f" | Submission URL: {submission_url}"
        for key, value in kwargs.items():
            context += f" | {key}: {value}"
        logger.info(f"🚀 Starting {operation} - {context}")

    def _log_operation_success(self, operation: str, submission_url: str = None, **kwargs):
        """Log successful database operation with full context"""
        context = f"Supabase Project: {self.supabase_project}"
        if submission_url:
            context += f" | Submission URL: {submission_url}"
        for key, value in kwargs.items():
            context += f" | {key}: {value}"
        logger.info(f"✅ {operation} SUCCESS - {context}")

    def _log_operation_error(self, operation: str, error: str, submission_url: str = None, **kwargs):
        """Log failed database operation with full context"""
        context = f"Supabase Project: {self.supabase_project} | URL: {self.supabase_url}"
        if submission_url:
            context += f" | Submission URL: {submission_url}"
        for key, value in kwargs.items():
            context += f" | {key}: {value}"
        logger.error(f"❌ {operation} FAILED - {context} | Error: {error}")

    def list_recordings(self, path_prefix: str) -> List[str]:
        """List all audio file public URLs in the 'recordings' bucket under a given path_prefix."""
        operation = "LIST_RECORDINGS"
        
        if not path_prefix:
            self._log_operation_error(operation, "path_prefix is required", path_prefix=path_prefix)
            return []
            
        self._log_operation_start(operation, bucket="recordings", path_prefix=path_prefix)
        
        try:
            response = self.supabase.storage.from_('recordings').list(path=path_prefix)
            recording_urls = []
            for file_object in response:
                if file_object.get('id') is not None:  # Ensure it's a file, not an empty folder
                    file_path_in_bucket = f"{path_prefix}/{file_object['name']}"
                    public_url = self.supabase.storage.from_('recordings').get_public_url(file_path_in_bucket)
                    recording_urls.append(public_url)
            
            self._log_operation_success(operation, 
                                      bucket="recordings", 
                                      path_prefix=path_prefix, 
                                      files_found=len(recording_urls),
                                      urls=recording_urls[:3] if recording_urls else [])  # Log first 3 URLs for verification
            return recording_urls
        except Exception as e:
            self._log_operation_error(operation, str(e), bucket="recordings", path_prefix=path_prefix)
            return []

    def update_submission_results(self, 
                                  submission_url: str, 
                                  question_results: Dict[str, Any], 
                                  recordings: Optional[List[str]] = None, 
                                  overall_assignment_score: Optional[Dict[str, Any]] = None, # Expects a Dict for JSON
                                  duration_feedback: Optional[list] = None # <-- add this
                                  ) -> Optional[str]:
        """Update an existing submission with analysis results, recordings, and overall assignment score (as JSON)."""
        operation = "UPDATE_SUBMISSION_RESULTS"
        
        log_kwargs = {
            "submission_url": submission_url,
            "questions_count": len(question_results) if question_results else 0,
            "recordings_count": len(recordings) if recordings else 0,
            "table": "submissions"
        }
        if overall_assignment_score is not None:
            # Log the JSON content directly or a summary of it
            log_kwargs["overall_assignment_score"] = json.dumps(overall_assignment_score) 

        self._log_operation_start(operation, **log_kwargs)
        
        try:
            # First, check if the submission exists
            logger.info(f"🔍 Looking for existing submission with ID: {submission_url}")
            existing_result = self.supabase.table('submissions').select("id, status").eq('id', submission_url).execute()
            
            if not existing_result.data or len(existing_result.data) == 0:
                self._log_operation_error(operation, f"No submission found with ID: {submission_url}", submission_url=submission_url, table="submissions")
                return None
            
            submission_record = existing_result.data[0]
            logger.info(f"✅ Found existing submission: {submission_record['id']} with status: {submission_record['status']}")
            
            # Transform question_results to the new format
            transformed_results = self._transform_to_new_format(question_results, recordings or [], duration_feedback)
            
            # Log transformed results details
            logger.info(f"📊 Transformed results structure: {json.dumps(transformed_results, indent=2)}")
            logger.info(f"📊 Number of transformed results: {len(transformed_results)}")
            
            # Log duration feedback details
            if duration_feedback:
                logger.info(f"📊 Duration feedback received: {json.dumps(duration_feedback, indent=2)}")
                logger.info(f"📊 Number of duration feedback entries: {len(duration_feedback)}")
            else:
                logger.warning("⚠️ No duration feedback provided")
            
            # Prepare update data with the transformed results
            update_data = {
                "section_feedback": transformed_results,
                "status": "graded"
            }
            
            # Add recordings if provided
            if recordings:
                update_data["recordings"] = recordings

            # Add overall_assignment_score (JSON object) if provided
            if overall_assignment_score is not None:
                update_data["overall_assignment_score"] = overall_assignment_score # Supabase client handles dict as JSON
            
            # Log the data being updated
            log_message_parts = [
                f"status=graded",
                f"recordings_count={len(recordings or [])}",
                f"section_feedback_size={len(json.dumps(transformed_results)) if transformed_results else 0} bytes"
            ]
            if overall_assignment_score is not None:
                log_message_parts.append(f"overall_assignment_score={json.dumps(overall_assignment_score)}")

            logger.info(f"📝 Data to update for {submission_url}: {', '.join(log_message_parts)}")

            # Update the submission
            result = self.supabase.table('submissions').update(update_data).eq('id', submission_url).execute()
            
            if result.data and len(result.data) > 0:
                updated_submission = result.data[0]
                submission_db_id = updated_submission['id']
                
                # Log the updated submission data
                logger.info(f"📊 Updated submission data: {json.dumps(updated_submission, indent=2)}")
                
                success_log_kwargs = {
                    "submission_url": submission_url,
                    "db_id": submission_db_id,
                    "table": "submissions",
                    "status": "graded"
                }
                if overall_assignment_score is not None:
                    success_log_kwargs["overall_assignment_score"] = json.dumps(overall_assignment_score)
                
                self._log_operation_success(operation, **success_log_kwargs)
                return submission_db_id
            else:
                error_msg = result.error if hasattr(result, 'error') and result.error else 'No data returned from update operation'
                self._log_operation_error(operation, error_msg, submission_url=submission_url, table="submissions")
                logger.error(f"📊 Full Supabase response: {result}")
                return None
        except Exception as e:
            self._log_operation_error(operation, str(e), submission_url=submission_url, table="submissions")
            return None

    def update_section_feedback(self, submission_id: str, section_feedback: Dict[str, Any]) -> bool:
        """Update the section_feedback column for a submission."""
        operation = "UPDATE_SECTION_FEEDBACK"
        
        self._log_operation_start(operation,
                                submission_id=submission_id,
                                table="submissions",
                                feedback_size=len(json.dumps(section_feedback)) if section_feedback else 0)
        
        try:
            result = self.supabase.table('submissions').update({
                "section_feedback": section_feedback
            }).eq('id', submission_id).execute()
            
            if result.error:
                self._log_operation_error(operation, str(result.error), submission_id=submission_id, table="submissions")
                return False
            
            self._log_operation_success(operation, submission_id=submission_id, table="submissions")
            return True
        except Exception as e:
            self._log_operation_error(operation, str(e), submission_id=submission_id, table="submissions")
            return False

    def _transform_to_new_format(self, question_results: Dict[str, Any], recordings: List[str], duration_feedback: Optional[list] = None) -> List[Dict[str, Any]]:
        """Transform old question_results format to new standardized array format, with optional duration_feedback per question."""
        transformed_results = []
        duration_feedback_map = {str(fb['question_number']): fb for fb in (duration_feedback or [])}
        
        # Log duration feedback mapping
        for question_id, analysis_results in question_results.items():
            # OPTION 1: Prioritize original_audio_url from analysis results
            audio_url = ""
            
            # First, try to get the original audio URL from analysis results
            if isinstance(analysis_results, dict) and "original_audio_url" in analysis_results:
                audio_url = analysis_results["original_audio_url"]
                logger.info(f"📎 Using original_audio_url from analysis results for question {question_id}: {audio_url}")
            
            # Fallback: Get audio URL from recordings list (old method)
            if not audio_url and recordings:
                # Try to find recording for this question
                for recording in recordings:
                    if f"question_{question_id}" in recording or f"q{question_id}" in recording:
                        audio_url = recording
                        break
                # If no specific match, use recording by index (question_id - 1)
                if not audio_url:
                    try:
                        question_index = int(question_id) - 1
                        if 0 <= question_index < len(recordings):
                            audio_url = recordings[question_index]
                            logger.info(f"📎 Using recording by index for question {question_id}: {audio_url}")
                    except (ValueError, IndexError):
                        # If question_id is not a number or index is out of range, use first recording
                        if recordings:
                            audio_url = recordings[0]
                            logger.info(f"📎 Using first recording as fallback for question {question_id}: {audio_url}")
            
            # Extract transcript from multiple possible sources
            transcript = ""

            # Option 1: Look for transcript at the top level of analysis results (new architecture)
            if isinstance(analysis_results, dict) and "transcript" in analysis_results:
                transcript = analysis_results["transcript"] or ""
                logger.info(f"📝 Using transcript from analysis results for question {question_id}")

            # Option 2: Fallback to pronunciation result (old architecture)  
            if not transcript and "pronunciation" in analysis_results and isinstance(analysis_results["pronunciation"], dict):
                transcript = analysis_results["pronunciation"].get("transcript", "")
                logger.info(f"📝 Using transcript from pronunciation results for question {question_id}")
            
            # Build section_feedback from analysis results
            section_feedback = {}
            
            # Add each analysis type if it exists and has the expected format
            for analysis_type in ["fluency", "grammar", "lexical", "pronunciation"]:
                if analysis_type in analysis_results:
                    result = analysis_results[analysis_type]
                    if isinstance(result, dict) and "grade" in result and "issues" in result:
                        section_feedback[analysis_type] = result
                    else:
                        # Handle old format or error cases
                        section_feedback[analysis_type] = {
                            "grade": 0,
                            "issues": [f"Error in {analysis_type} analysis: {result.get('error', 'Unknown error')}"]
                        }
            
            transformed_result = {
                "audio_url": audio_url,
                "transcript": transcript,
                "question_id": int(question_id),
                "section_feedback": section_feedback
            }
            # Attach duration_feedback if available for this question
            if duration_feedback_map.get(str(question_id)):
                logger.info(f"Attaching duration_feedback to question_id {question_id}: {duration_feedback_map[str(question_id)]}")
                transformed_result["duration_feedback"] = duration_feedback_map[str(question_id)]
            else:
                logger.info(f"No duration_feedback for question_id {question_id}")
            
            transformed_results.append(transformed_result)
        
        logger.info(f"Final transformed_results for submission: {json.dumps(transformed_results, indent=2)}")
        return transformed_results

    def get_submission_by_url(self, submission_url: str) -> Optional[Dict[str, Any]]:
        """Fetch a submission row by submission_url (id)."""
        try:
            result = self.supabase.table('submissions').select('*').eq('id', submission_url).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching submission by url {submission_url}: {str(e)}")
            return None

    def get_assignment_by_id(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        """Fetch an assignment row by assignment_id (id)."""
        try:
            result = self.supabase.table('assignments').select('*').eq('id', assignment_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching assignment by id {assignment_id}: {str(e)}")
            return None
