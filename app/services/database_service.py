from app.core.config import supabase, SUPABASE_URL
import logging
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

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
                                  duration_feedback: Optional[list] = None, # <-- add this
                                  test_logs: Optional[Dict[str, Any]] = None # <-- add test_logs
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
            existing_result = self.supabase.table('submissions').select("id, status, assignment_id").eq('id', submission_url).execute()
            
            if not existing_result.data or len(existing_result.data) == 0:
                self._log_operation_error(operation, f"No submission found with ID: {submission_url}", submission_url=submission_url, table="submissions")
                return None
            
            submission_record = existing_result.data[0]
            logger.info(f"✅ Found existing submission: {submission_record['id']} with status: {submission_record['status']}")
            
            # Get assignment meta to check autoGrade setting
            assignment_id = submission_record.get('assignment_id')
            if assignment_id:
                assignment_result = self.supabase.table('assignments').select('metadata').eq('id', assignment_id).execute()
                if assignment_result.data and len(assignment_result.data) > 0:
                    metadata = assignment_result.data[0].get('metadata', {})
                    auto_grade = metadata.get('autoGrade', True)  # Default to True if not specified
                    logger.info(f"📊 Assignment {assignment_id} autoGrade setting: {auto_grade}")
                else:
                    logger.warning(f"⚠️ Could not find assignment {assignment_id}, defaulting to autoGrade=True")
                    auto_grade = True
            else:
                logger.warning(f"⚠️ No assignment_id found for submission {submission_url}, defaulting to autoGrade=True")
                auto_grade = True
            
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
                "status": "awaiting_review" if not auto_grade else "graded"
            }
            
            # Add recordings if provided
            if recordings:
                update_data["recordings"] = recordings

            # Add overall_assignment_score (JSON object) if provided
            if overall_assignment_score is not None:
                update_data["overall_assignment_score"] = overall_assignment_score # Supabase client handles dict as JSON
                
                # Extract IELTS overall band score for the grade column
                ielts_overall_band = overall_assignment_score.get("ielts_overall_band")
                if ielts_overall_band is not None:
                    update_data["grade"] = ielts_overall_band
                    logger.info(f"🎯 Setting grade column to IELTS overall band: {ielts_overall_band}")
                else:
                    logger.warning("⚠️ No IELTS overall band score found in overall_assignment_score")
            
            # Add test_logs if provided
            if test_logs is not None:
                update_data["test_logs"] = test_logs
                logger.info(f"📝 Adding test_logs with {len(test_logs)} entries")
            
            # Log the data being updated
            log_message_parts = [
                f"status={update_data['status']}",
                f"recordings_count={len(recordings or [])}",
                f"section_feedback_size={len(json.dumps(transformed_results)) if transformed_results else 0} bytes"
            ]
            if overall_assignment_score is not None:
                log_message_parts.append(f"overall_assignment_score={json.dumps(overall_assignment_score)}")
            if "grade" in update_data:
                log_message_parts.append(f"grade={update_data['grade']}")

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
                    "status": update_data['status']
                }
                if overall_assignment_score is not None:
                    success_log_kwargs["overall_assignment_score"] = json.dumps(overall_assignment_score)
                if "grade" in update_data:
                    success_log_kwargs["grade"] = update_data["grade"]
                
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
        
        # Add version at the top of the array
        transformed_results.append({"version": "v3"})
        
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
            
            # Extract clean transcript (added for filler word removal)
            clean_transcript = ""
            if isinstance(analysis_results, dict) and "clean_transcript" in analysis_results:
                clean_transcript = analysis_results["clean_transcript"] or ""
                logger.info(f"🧹 Using clean transcript from analysis results for question {question_id}")
            else:
                # Fallback: if no clean transcript available, use original transcript
                clean_transcript = transcript
                logger.info(f"🧹 No clean transcript found, using original transcript for question {question_id}")
            
            # Build section_feedback from analysis results
            section_feedback = {}
            #w
            # Add each analysis type if it exists and has the expected format
            for analysis_type in ["fluency", "grammar", "lexical", "pronunciation", "paragraph_restructuring", "vocabulary"]:
                if analysis_type in analysis_results:
                    result = analysis_results[analysis_type]
                    if isinstance(result, dict):
                        if analysis_type == "vocabulary":
                            # Special handling for vocabulary analysis
                            section_feedback[analysis_type] = {
                                "grade": result.get("grade", 0),
                                "vocabulary_suggestions": result.get("vocabulary_suggestions", {}),
                                "issues": [f"Found {len(result.get('vocabulary_suggestions', {}))} vocabulary suggestions"]
                            }
                        elif analysis_type == "grammar":
                            # Special handling for grammar analysis
                            section_feedback[analysis_type] = {
                                "grade": result.get("grade", 0),
                                "grammar_corrections": result.get("grammar_corrections", {}),
                                "issues": [f"Found {len(result.get('grammar_corrections', {}))} grammar corrections"]
                            }
                        elif analysis_type == "paragraph_restructuring":
                            # Simple handling for paragraph restructuring - no grade/issues needed
                            section_feedback[analysis_type] = {
                                "original_band": result.get("original_band", ""),
                                "target_band": result.get("target_band", ""), 
                                "improved_transcript": result.get("improved_transcript", "")
                            }
                        elif "grade" in result and "issues" in result:
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
                "clean_transcript": clean_transcript,
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

    def get_user_email_by_student_id(self, student_id: str) -> Optional[str]:
        """Fetch user email by student_id from users table."""
        try:
            result = self.supabase.table('users').select('email').eq('id', student_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0].get('email')
            return None
        except Exception as e:
            logger.error(f"Error fetching user email by student_id {student_id}: {str(e)}")
            return None

    def get_user_name_by_student_id(self, student_id: str) -> Optional[str]:
        """Fetch user name by student_id from users table."""
        try:
            result = self.supabase.table('users').select('name').eq('id', student_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0].get('name')
            return None
        except Exception as e:
            logger.error(f"Error fetching user name by student_id {student_id}: {str(e)}")
            return None

    async def update_status_logs(self, submission_url: str, question_number: int, analysis_type: str, status: str) -> bool:
        """Update the status logs for a specific analysis type in a question."""
        operation = "UPDATE_STATUS_LOGS"
        
        self._log_operation_start(operation,
                                submission_url=submission_url,
                                question_number=question_number,
                                analysis_type=analysis_type,
                                status=status)
        
        try:
            # First get the current submission
            submission = self.get_submission_by_url(submission_url)
            if not submission:
                self._log_operation_error(operation, f"Submission not found: {submission_url}")
                return False
            
            # Get current status logs or initialize new ones
            current_logs = submission.get('status_logs', {})
            if not current_logs:
                current_logs = {
                    "submission_started": datetime.now().isoformat(),
                    "total_questions": submission.get('total_questions', 1),
                    "questions": {}
                }
            
            # Initialize question status if not exists, preserving existing statuses
            question_key = str(question_number)
            if question_key not in current_logs["questions"]:
                current_logs["questions"][question_key] = {
                    "pronunciation": "not_started",
                    "fluency": "not_started",
                    "grammar": "not_started",
                    "vocabulary": "not_started",
                    "started_at": datetime.now().isoformat()
                }
            else:
                # Preserve existing question status and only add missing analysis types
                existing_question = current_logs["questions"][question_key]
                default_statuses = {
                    "pronunciation": "not_started",
                    "fluency": "not_started", 
                    "grammar": "not_started",
                    "vocabulary": "not_started"
                }
                for analysis_key, default_status in default_statuses.items():
                    if analysis_key not in existing_question:
                        existing_question[analysis_key] = default_status
                if "started_at" not in existing_question:
                    existing_question["started_at"] = datetime.now().isoformat()
            
            # Update the specific analysis status
            current_logs["questions"][question_key][analysis_type] = status
            
            # Add API call counts to status logs
            try:
                from app.services.api_call_tracker import api_call_tracker
                call_counts = await api_call_tracker.get_submission_call_counts(submission_url)
                current_logs["api_call_counts"] = call_counts
            except Exception as e:
                logger.warning(f"Failed to add API call counts to status logs: {str(e)}")
            
            # Update the submission
            result = self.supabase.table('submissions').update({
                "status_logs": current_logs
            }).eq('id', submission_url).execute()
            
            # Check if the update was successful by looking at the data
            if not result.data:
                self._log_operation_error(operation, "No data returned from update operation")
                return False
            
            self._log_operation_success(operation,
                                      submission_url=submission_url,
                                      question_number=question_number,
                                      analysis_type=analysis_type,
                                      status=status)
            return True
        
        except Exception as e:
            self._log_operation_error(operation, str(e))
            return False

    def update_submission_status_logs(self, submission_url: str, status_logs: Dict[str, Any]) -> bool:
        """Update the entire status logs for a submission."""
        operation = "UPDATE_SUBMISSION_STATUS_LOGS"
        
        self._log_operation_start(operation,
                                submission_url=submission_url,
                                status_logs_size=len(str(status_logs)))
        
        try:
            # First check if the submission exists
            submission = self.get_submission_by_url(submission_url)
            if not submission:
                self._log_operation_error(operation, f"Submission not found: {submission_url}")
                return False
            
            # Update the submission with the new status logs
            result = self.supabase.table('submissions').update({
                "status_logs": status_logs
            }).eq('id', submission_url).execute()
            
            # Check if the update was successful by looking at the data
            if not result.data:
                self._log_operation_error(operation, "No data returned from update operation")
                return False
            
            self._log_operation_success(operation,
                                      submission_url=submission_url,
                                      status_logs_size=len(str(status_logs)))
            return True
        
        except Exception as e:
            self._log_operation_error(operation, str(e))
            return False

    def get_transformed_results(self, submission_url: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve transformed results from database"""
        operation = f"get_transformed_results for {submission_url}"

        try:
            submission = self.get_submission_by_url(submission_url)
            if submission and submission.get('section_feedback'):
                return submission['section_feedback']
            return None
        except Exception as e:
            self._log_operation_error(operation, str(e))
            return None

    # ============================================
    # Stripe Subscription Methods
    # ============================================

    def create_subscription(
        self,
        teacher_id: str,
        stripe_customer_id: str,
        stripe_subscription_id: str,
        stripe_price_id: str,
        plan_type: str,
        billing_cycle: str,
        student_count: int,
        current_period_start: datetime,
        current_period_end: datetime
    ) -> Optional[str]:
        """Create a new subscription record

        Args:
            teacher_id: Teacher's user ID
            stripe_customer_id: Stripe customer ID
            stripe_subscription_id: Stripe subscription ID
            stripe_price_id: Stripe price ID
            plan_type: "30min" or "60min"
            billing_cycle: "monthly" or "quarterly"
            student_count: Number of students
            current_period_start: Billing period start
            current_period_end: Billing period end

        Returns:
            Subscription ID if successful, None otherwise
        """
        operation = "CREATE_SUBSCRIPTION"

        self._log_operation_start(
            operation,
            teacher_id=teacher_id,
            plan_type=plan_type,
            billing_cycle=billing_cycle,
            student_count=student_count
        )

        try:
            result = self.supabase.table('teacher_subscriptions').insert({
                'teacher_id': teacher_id,
                'stripe_customer_id': stripe_customer_id,
                'stripe_subscription_id': stripe_subscription_id,
                'stripe_price_id': stripe_price_id,
                'plan_type': plan_type,
                'billing_cycle': billing_cycle,
                'student_count': student_count,
                'status': 'active',
                'current_period_start': current_period_start.isoformat(),
                'current_period_end': current_period_end.isoformat(),
                'cancel_at_period_end': False
            }).execute()

            if result.data and len(result.data) > 0:
                subscription_id = result.data[0]['id']
                self._log_operation_success(operation, teacher_id=teacher_id, subscription_id=subscription_id)
                return subscription_id
            else:
                self._log_operation_error(operation, "No data returned", teacher_id=teacher_id)
                return None

        except Exception as e:
            self._log_operation_error(operation, str(e), teacher_id=teacher_id)
            return None

    def get_subscription_by_teacher_id(self, teacher_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription record for a teacher

        Args:
            teacher_id: Teacher's user ID

        Returns:
            Subscription dict if found, None otherwise
        """
        try:
            result = self.supabase.table('teacher_subscriptions').select('*').eq('teacher_id', teacher_id).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error fetching subscription for teacher {teacher_id}: {str(e)}")
            return None

    def update_subscription(
        self,
        teacher_id: str,
        updates: Dict[str, Any]
    ) -> bool:
        """Update subscription record

        Args:
            teacher_id: Teacher's user ID
            updates: Dict of fields to update

        Returns:
            True if successful, False otherwise
        """
        operation = "UPDATE_SUBSCRIPTION"

        self._log_operation_start(operation, teacher_id=teacher_id, updates=list(updates.keys()))

        try:
            result = self.supabase.table('teacher_subscriptions').update(updates).eq('teacher_id', teacher_id).execute()

            if result.data:
                self._log_operation_success(operation, teacher_id=teacher_id)
                return True
            else:
                self._log_operation_error(operation, "No data returned", teacher_id=teacher_id)
                return False

        except Exception as e:
            self._log_operation_error(operation, str(e), teacher_id=teacher_id)
            return False

    def update_teacher_credits(self, teacher_id: str, credits: float) -> bool:
        """Update teacher's credit balance

        Args:
            teacher_id: Teacher's user ID
            credits: New credit amount (in hours)

        Returns:
            True if successful, False otherwise
        """
        operation = "UPDATE_TEACHER_CREDITS"

        self._log_operation_start(operation, teacher_id=teacher_id, credits=credits)

        try:
            result = self.supabase.table('users').update({'credits': credits}).eq('id', teacher_id).execute()

            if result.data:
                self._log_operation_success(operation, teacher_id=teacher_id, credits=credits)
                return True
            else:
                self._log_operation_error(operation, "No data returned", teacher_id=teacher_id)
                return False

        except Exception as e:
            self._log_operation_error(operation, str(e), teacher_id=teacher_id)
            return False

    def delete_subscription(self, teacher_id: str) -> bool:
        """Delete subscription record (used when subscription is canceled)

        Args:
            teacher_id: Teacher's user ID

        Returns:
            True if successful, False otherwise
        """
        operation = "DELETE_SUBSCRIPTION"

        self._log_operation_start(operation, teacher_id=teacher_id)

        try:
            result = self.supabase.table('teacher_subscriptions').delete().eq('teacher_id', teacher_id).execute()

            if result.data is not None:
                self._log_operation_success(operation, teacher_id=teacher_id)
                return True
            else:
                self._log_operation_error(operation, "No data returned", teacher_id=teacher_id)
                return False

        except Exception as e:
            self._log_operation_error(operation, str(e), teacher_id=teacher_id)
            return False
