from app.core.config import supabase
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.supabase = supabase

    def list_recordings(self, path_prefix: str) -> List[str]:
        """List all audio file public URLs in the 'recordings' bucket under a given path_prefix."""
        if not path_prefix:
            logger.warning("path_prefix is required to list specific recordings.")
            return []
        try:
            response = self.supabase.storage.from_('recordings').list(path=path_prefix)
            recording_urls = []
            for file_object in response:
                if file_object.get('id') is not None:  # Ensure it's a file, not an empty folder
                    file_path_in_bucket = f"{path_prefix}/{file_object['name']}"
                    public_url = self.supabase.storage.from_('recordings').get_public_url(file_path_in_bucket)
                    recording_urls.append(public_url)
            logger.info(f"Found {len(recording_urls)} files in 'recordings' bucket under path '{path_prefix}'.")
            return recording_urls
        except Exception as e:
            logger.error(f"Error listing recordings under '{path_prefix}': {str(e)}")
            return []

    def insert_submission(self, submission_url: str, question_results: Dict[str, Any], recordings: Optional[List[str]] = None) -> Optional[str]:
        """Insert a new submission row with section_feedback and recordings."""
        try:
            section_feedback = {
                "submission_url": submission_url,
                "question_results": question_results
            }
            # Ensure all required fields from the table definition are considered
            # assignment_id, student_id, attempt, grade, valid_transcrip are nullable or have defaults
            data_to_insert = {
                "section_feedback": section_feedback,
                "recordings": recordings or [],
                "status": "completed",  # Changed from "pending" as analysis is complete
                "submitted_at": "now()", # Utilizes Supabase/Postgres now()
                "submission_url": submission_url # Assuming submission_url itself should be stored if there's a dedicated column.
                                             # The schema image does not show a 'submission_url' column,
                                             # but it's good practice if it exists.
                                             # If not, remove this line. For now, I'll assume it might be useful
                                             # or implicitly mapped if `id` is not the submission_url.
                                             # Based on the schema, `id` is a uuid. `submission_url` seems to be a business key.
                                             # Let's check if there's a submission_url column.
                                             # The schema shows `id uuid`, `assignment_id uuid`, `student_id uuid`. No `submission_url` text column.
                                             # `section_feedback` already contains `submission_url`.
                                             # So, no dedicated `submission_url` top-level column needed in insert data.
            }

            # Corrected data_to_insert without a top-level submission_url, as it's in section_feedback
            # and not a direct column in the provided schema.
            final_data_to_insert = {
                "section_feedback": section_feedback,
                "recordings": recordings or [],
                "status": "completed",
                "submitted_at": "now()"
                # assignment_id, student_id, attempt etc. will use defaults or be NULL
            }

            result = self.supabase.table('submissions').insert(final_data_to_insert).execute()
            
            if result.data and len(result.data) > 0:
                submission_db_id = result.data[0]['id']
                logger.info(f"Inserted submission for {submission_url}. DB ID: {submission_db_id}")
                return submission_db_id
            else:
                logger.error(f"Failed to insert submission for {submission_url}. Response: {result.error or 'No data returned'}")
                return None
        except Exception as e:
            logger.error(f"Error inserting submission for {submission_url}: {str(e)}")
            return None

    def update_section_feedback(self, submission_id: str, section_feedback: Dict[str, Any]) -> bool:
        """Update the section_feedback column for a submission."""
        try:
            result = self.supabase.table('submissions').update({
                "section_feedback": section_feedback
            }).eq('id', submission_id).execute()
            if result.error:
                logger.error(f"Error updating section_feedback for submission {submission_id}: {result.error}")
                return False
            logger.info(f"Updated section_feedback for submission {submission_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating section_feedback for submission {submission_id}: {str(e)}")
            return False
