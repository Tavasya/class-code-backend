import os
import json
import logging
import re
import aiohttp
import tempfile
import asyncio
import subprocess
import azure.cognitiveservices.speech as speechsdk
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from app.core.config import OPENAI_API_KEY, AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, OPENAI_API_URL
from app.services.file_manager_service import FileManagerService
import unicodedata
import cmudict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestLogsManager:
    """Manages test logs for tracking errors and debugging"""
    
    def __init__(self):
        self.logs = {
            "memory_errors": [],
            "assembly_errors": [],
            "pronunciation_errors": [],
            "file_not_found_errors": [],
            "azure_speech_errors": [],
            "processing_timeline": [],
            "workflow_steps": [],
            "cleanup_operations": [],
            "memory_snapshots": []
        }
        self._start_time = datetime.now(timezone.utc)
        
    def _get_elapsed_time(self) -> float:
        """Get elapsed time since start in seconds"""
        return (datetime.now(timezone.utc) - self._start_time).total_seconds()
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def log_memory_error(self, error_type: str, details: str, memory_usage: float = None):
        """Log memory-related errors"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": error_type,
            "details": details,
            "memory_usage_mb": memory_usage
        }
        self.logs["memory_errors"].append(entry)
        logger.warning(f"💾 Memory Error: {error_type} - {details}")
    
    def log_file_not_found_error(self, file_path: str, attempt: int, max_attempts: int, details: str = None):
        """Log file not found errors"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "file_path": file_path,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "details": details
        }
        self.logs["file_not_found_errors"].append(entry)
        logger.warning(f"📁 File Not Found: {file_path} (attempt {attempt}/{max_attempts})")
    
    def log_azure_speech_error(self, error_type: str, details: str, audio_file: str = None):
        """Log Azure Speech Service errors"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": error_type,
            "details": details,
            "audio_file": audio_file
        }
        self.logs["azure_speech_errors"].append(entry)
        logger.warning(f"🎤 Azure Speech Error: {error_type} - {details}")
    
    def log_pronunciation_error(self, error_type: str, details: str, audio_file: str = None):
        """Log pronunciation analysis errors"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error_type": error_type,
            "details": details,
            "audio_file": audio_file
        }
        self.logs["pronunciation_errors"].append(entry)
        logger.warning(f"🔊 Pronunciation Error: {error_type} - {details}")
    
    def log_processing_step(self, step: str, status: str, details: str = None):
        """Log processing timeline"""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "step": step,
            "status": status,
            "details": details
        }
        self.logs["processing_timeline"].append(entry)
        logger.info(f"📊 Processing Step: {step} - {status}")
    
    def log_workflow_step(self, step_name: str, action: str, details: str = None, file_path: str = None):
        """Log workflow step with memory snapshot"""
        memory_mb = self._get_memory_usage()
        elapsed_s = self._get_elapsed_time()
        
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed_s, 2),
            "step_name": step_name,
            "action": action,
            "memory_mb": round(memory_mb, 1),
            "details": details,
            "file_path": file_path
        }
        self.logs["workflow_steps"].append(entry)
        logger.info(f"🔄 Workflow: {step_name} - {action} (Memory: {memory_mb:.1f}MB, T+{elapsed_s:.1f}s)")
    
    def log_cleanup_operation(self, operation: str, target: str, status: str, details: str = None):
        """Log cleanup operations"""
        memory_mb = self._get_memory_usage()
        elapsed_s = self._get_elapsed_time()
        
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed_s, 2),
            "operation": operation,
            "target": target,
            "status": status,
            "memory_mb": round(memory_mb, 1),
            "details": details
        }
        self.logs["cleanup_operations"].append(entry)
        logger.info(f"🧹 Cleanup: {operation} - {target} - {status} (Memory: {memory_mb:.1f}MB)")
    
    def take_memory_snapshot(self, checkpoint: str, context: str = None):
        """Take a memory snapshot at a specific checkpoint"""
        memory_mb = self._get_memory_usage()
        elapsed_s = self._get_elapsed_time()
        
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(elapsed_s, 2),
            "checkpoint": checkpoint,
            "memory_mb": round(memory_mb, 1),
            "context": context
        }
        self.logs["memory_snapshots"].append(entry)
        logger.debug(f"📸 Memory Snapshot: {checkpoint} - {memory_mb:.1f}MB (T+{elapsed_s:.1f}s)")
    
    def get_logs(self) -> Dict[str, Any]:
        """Get all logs as dictionary"""
        # Add summary statistics
        final_logs = self.logs.copy()
        final_logs["summary"] = {
            "total_elapsed_seconds": round(self._get_elapsed_time(), 2),
            "final_memory_mb": round(self._get_memory_usage(), 1),
            "workflow_steps_count": len(self.logs["workflow_steps"]),
            "cleanup_operations_count": len(self.logs["cleanup_operations"]),
            "memory_snapshots_count": len(self.logs["memory_snapshots"]),
            "error_counts": {
                "memory_errors": len(self.logs["memory_errors"]),
                "file_not_found_errors": len(self.logs["file_not_found_errors"]),
                "azure_speech_errors": len(self.logs["azure_speech_errors"]),
                "pronunciation_errors": len(self.logs["pronunciation_errors"])
            }
        }
        return final_logs

# Initialize CMU Dictionary
cmu = cmudict.dict()

# Azure Speech config
SPEECH_KEY = AZURE_SPEECH_KEY
REGION = AZURE_SPEECH_REGION

# OpenAI API config for improvement suggestions
OPENAI_URL = OPENAI_API_URL

# Azure phoneme to CMU mapping
AZURE_TO_CMU = {
    "ax": "AH",  # schwa
    "ay": "AY",  # PRICE vowel
    "ow": "OW",  # GOAT vowel
    "iy": "IY",  # FLEECE vowel
    "ih": "IH",  # KIT vowel
    "eh": "EH",  # DRESS vowel
    "ae": "AE",  # TRAP vowel
    "aa": "AA",  # PALM vowel
    "ao": "AO",  # THOUGHT vowel
    "uw": "UW",  # GOOSE vowel
    "uh": "UH",  # FOOT vowel
    "er": "ER"   # NURSE vowel
}

# Stress mark symbols
STRESS_MARKS = {
    "1": "ˈ",  # Primary stress
    "2": "ˌ"   # Secondary stress
}

# Azure phoneme to IPA mapping
AZURE_TO_IPA = {
    # Vowels
    "ax": "ə",  # schwa
    "ay": "aɪ",  # PRICE vowel
    "ow": "oʊ",  # GOAT vowel
    "iy": "i",   # FLEECE vowel
    "ih": "ɪ",   # KIT vowel
    "eh": "ɛ",   # DRESS vowel
    "ae": "æ",   # TRAP vowel
    "aa": "ɑ",   # PALM vowel
    "ao": "ɔ",   # THOUGHT vowel
    "uw": "u",   # GOOSE vowel
    "uh": "ʊ",   # FOOT vowel
    "er": "ɜr",  # NURSE vowel
    # Consonants
    "dh": "ð",   # voiced th
    "th": "θ",   # voiceless th
    "sh": "ʃ",   # SHIP consonant
    "zh": "ʒ",   # MEASURE consonant
    "ch": "tʃ",  # CHIP consonant
    "jh": "dʒ",  # JUDGE consonant
    "ng": "ŋ",   # SING consonant
    # Stress markers
    "1": "ˈ",    # primary stress
    "2": "ˌ",    # secondary stress
    # Keep single letters as is
    "p": "p", "b": "b", "t": "t", "d": "d", "k": "k", "g": "g",
    "f": "f", "v": "v", "s": "s", "z": "z", "h": "h",
    "m": "m", "n": "n", "l": "l", "r": "r", "w": "w", "y": "j"
}

class PronunciationService:
    """Service for handling pronunciation assessment"""
    
    @staticmethod
    def get_cmu_pronunciation(word: str) -> List[str]:
        """Get CMU pronunciation for a word"""
        try:
            # Get pronunciation from CMU dict
            word = word.lower()
            if word in cmu:
                # Return first pronunciation (most common)
                return cmu[word][0]
            return []
        except Exception as e:
            logger.warning(f"Failed to get CMU pronunciation for {word}: {str(e)}")
            return []

    @staticmethod
    def align_phonemes(azure_phonemes: List[str], cmu_pronunciation: List[str]) -> List[Dict[str, Any]]:
        """Align Azure phonemes with CMU pronunciation for stress marking"""
        aligned = []
        vowel_index = 0
        
        for az_phoneme in azure_phonemes:
            alignment = {
                "azure_phoneme": az_phoneme,
                "ipa": AZURE_TO_IPA.get(az_phoneme, az_phoneme),
                "stress": None
            }
            
            # Check if current phoneme is a vowel
            if az_phoneme in AZURE_TO_CMU:
                cmu_base = AZURE_TO_CMU[az_phoneme]
                # Find corresponding CMU vowel
                for cmu_phoneme in cmu_pronunciation:
                    if cmu_phoneme.rstrip('012').upper() == cmu_base:
                        # Extract stress if present
                        stress = next((c for c in cmu_phoneme if c.isdigit()), None)
                        if stress:
                            alignment["stress"] = STRESS_MARKS.get(stress)
                        break
                vowel_index += 1
                
            aligned.append(alignment)
            
        return aligned

    @staticmethod
    def process_phoneme(azure_phoneme: str, stress: Optional[str] = None) -> str:
        """Process a single phoneme with stress marking"""
        # Get base IPA symbol
        ipa = AZURE_TO_IPA.get(azure_phoneme, azure_phoneme)
        
        # Apply stress if present
        if stress:
            return stress + ipa
        return ipa

    @staticmethod
    def convert_to_ipa_with_stress(word: str, azure_phonemes: List[str]) -> str:
        """Convert Azure phonemes to IPA with stress marks using CMU dict"""
        try:
            # Get CMU pronunciation
            cmu_pron = PronunciationService.get_cmu_pronunciation(word)
            if not cmu_pron:
                # Fallback to basic IPA conversion if no CMU pronunciation found
                return "".join(PronunciationService.convert_to_ipa(p) for p in azure_phonemes)
            
            # Align phonemes and get stress information
            aligned = PronunciationService.align_phonemes(azure_phonemes, cmu_pron)
            
            # Convert to IPA with stress marks
            result = ""
            for alignment in aligned:
                result += PronunciationService.process_phoneme(
                    alignment["azure_phoneme"],
                    alignment["stress"]
                )
            
            return result
            
        except Exception as e:
            logger.warning(f"Failed to convert to IPA with stress for {word}: {str(e)}")
            # Fallback to basic IPA conversion
            return "".join(PronunciationService.convert_to_ipa(p) for p in azure_phonemes)

    @staticmethod
    def convert_to_ipa(phoneme: str) -> str:
        """Convert Azure phoneme to IPA symbol"""
        # First normalize the input phoneme
        phoneme = phoneme.strip().lower()
        
        # Check for stress markers in the phoneme
        stress_marker = ""
        if phoneme.endswith("1"):
            stress_marker = "ˈ"
            phoneme = phoneme[:-1]
        elif phoneme.endswith("2"):
            stress_marker = "ˌ"
            phoneme = phoneme[:-1]
        
        # Get the IPA symbol
        ipa_symbol = AZURE_TO_IPA.get(phoneme, phoneme)
        
        # Return the combination of stress marker and IPA symbol
        return stress_marker + ipa_symbol
    
    @staticmethod
    def extract_reference_phonemes(word_data):
        """Extract reference phonemes from Azure word data with stress marks"""
        phonemes = word_data.get("Phonemes", [])
        if not phonemes:
            return "", []
        
        # Extract the word and phoneme names
        word = word_data.get("Word", "").lower()
        phoneme_list = []
        phoneme_details = []
        
        # Get Azure phonemes
        azure_phonemes = [p.get("Phoneme", "") for p in phonemes]
        
        # Convert to IPA with stress marks using CMU dict
        ipa_with_stress = PronunciationService.convert_to_ipa_with_stress(word, azure_phonemes)
        
        # Process each phoneme with its details
        for i, phoneme_data in enumerate(phonemes):
            phoneme = phoneme_data.get("Phoneme", "")
            if isinstance(phoneme, bytes):
                phoneme = phoneme.decode('utf-8')
            
            # Get the processed IPA symbol with stress
            processed_phoneme = PronunciationService.convert_to_ipa_with_stress(
                word,
                [phoneme]
            )
            
            if processed_phoneme:
                phoneme_list.append(processed_phoneme)
                # Add detailed phoneme information
                phoneme_details.append({
                    "phoneme": processed_phoneme,
                    "accuracy_score": phoneme_data.get("PronunciationAssessment", {}).get("AccuracyScore", 0),
                    "error_type": phoneme_data.get("PronunciationAssessment", {}).get("ErrorType", "None")
                })
        
        # Return IPA string with stress marks and detailed phoneme list
        if phoneme_list:
            ipa_string = "/" + "".join(phoneme_list) + "/"
            ipa_string = unicodedata.normalize('NFC', ipa_string)
            return ipa_string, phoneme_details
        
        return "", []

    @staticmethod
    def chunk_text_into_phrases(reference_text: str) -> List[Dict[str, Any]]:
        """
        Break reference text into natural speech phrases/breath groups
        
        Args:
            reference_text: The text to be chunked into phrases
            
        Returns:
            List of phrase dictionaries with phrase text and metadata
        """
        try:
            import re
            
            if not reference_text or not reference_text.strip():
                return []
            
            phrases = []
            
            # Split on major punctuation and natural pause points
            sentences = re.split(r'[.!?]+', reference_text)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                
                # Split at commas first, then handle conjunctions more carefully
                comma_parts = sentence.split(',')
                parts = []
                
                for comma_part in comma_parts:
                    comma_part = comma_part.strip()
                    if not comma_part:
                        continue
                    
                    # Check for conjunctions at the beginning and split accordingly
                    conjunction_pattern = r'^\s*(and|but|or|so|however|therefore|although)\s+'
                    match = re.match(conjunction_pattern, comma_part, re.IGNORECASE)
                    
                    if match:
                        # Split at the conjunction
                        conjunction = match.group(1)
                        rest = comma_part[match.end():].strip()
                        if rest:  # Only add if there's content after the conjunction
                            parts.append(rest)
                    else:
                        parts.append(comma_part)
                
                for part in parts:
                    part = part.strip()
                    words = part.split()
                    
                    # Only create phrases with at least 2 words
                    if len(words) >= 2:
                        phrases.append({
                            "phrase": part,
                            "word_count": len(words),
                            "words": words,
                            "type": "breath_group"
                        })
                    elif len(words) == 1:
                        # Single words can be their own phrase (e.g., "Yes.", "No.")
                        phrases.append({
                            "phrase": part,
                            "word_count": 1,
                            "words": words,
                            "type": "single_word"
                        })
            
            # If no phrases were created (edge case), create one phrase from the whole text
            if not phrases and reference_text.strip():
                words = reference_text.strip().split()
                phrases.append({
                    "phrase": reference_text.strip(),
                    "word_count": len(words),
                    "words": words,
                    "type": "full_text"
                })
            
            return phrases
            
        except Exception as e:
            logger.warning(f"Error chunking text into phrases: {str(e)}")
            # Fallback: treat entire text as one phrase
            words = reference_text.strip().split() if reference_text else []
            return [{
                "phrase": reference_text.strip() if reference_text else "",
                "word_count": len(words),
                "words": words,
                "type": "fallback"
            }] if reference_text else []

    @staticmethod
    async def analyze_pronunciation(audio_file: str, reference_text: str, session_id: Optional[str] = None, test_logs: Optional[TestLogsManager] = None) -> Dict[str, Any]:
        """
        Analyze pronunciation using Azure Speech Services with a provided reference text
        
        Args:
            audio_file: Path to the local audio file (no longer accepts URLs)
            reference_text: Transcript text to use as reference
            session_id: Optional session ID for file lifecycle management
            
        Returns:
            Pronunciation assessment results in standardized format
        """
        try:
            # Initialize test logs if not provided
            if test_logs is None:
                test_logs = TestLogsManager()
            
            test_logs.log_workflow_step("pronunciation_analysis", "started", f"Reference text: {len(reference_text)} chars", audio_file)
            test_logs.take_memory_snapshot("analysis_start", "Beginning pronunciation analysis")
            
            # Validate that we have a local file path, not a URL
            if audio_file.startswith(('http://', 'https://')):
                error_msg = "PronunciationService now only accepts local file paths, not URLs. Audio URLs should be converted to local files by AudioService first."
                test_logs.log_pronunciation_error("invalid_input", error_msg, audio_file)
                raise ValueError(error_msg)
            
            # Verify file exists with retry mechanism
            max_wait_attempts = 5
            wait_time = 1  # Start with 1 second
            
            for attempt in range(max_wait_attempts):
                if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
                    file_size_mb = os.path.getsize(audio_file) / 1024 / 1024
                    test_logs.log_workflow_step("file_verification", "found", f"File ready after {attempt + 1} attempts, size: {file_size_mb:.2f}MB", audio_file)
                    test_logs.take_memory_snapshot("file_found", f"Audio file located and verified")
                    break
                    
                if attempt < max_wait_attempts - 1:
                    test_logs.log_file_not_found_error(audio_file, attempt + 1, max_wait_attempts, "File not ready, waiting...")
                    logger.info(f"Audio file not ready yet: {audio_file}. Waiting {wait_time}s (attempt {attempt + 1}/{max_wait_attempts})")
                    await asyncio.sleep(wait_time)
                    wait_time *= 1.5  # Exponential backoff
                else:
                    test_logs.log_file_not_found_error(audio_file, attempt + 1, max_wait_attempts, "File not found after all attempts - triggering retry")
                    logger.warning(f"Audio file not found after {max_wait_attempts} attempts: {audio_file}. File may have been cleaned up prematurely. Attempting to trigger audio pipeline retry.")
                    
                    # Try to get original audio URL and submission info from session_id
                    if session_id:
                        try:
                            file_manager_service = FileManagerService()
                            session_info = await file_manager_service.get_session_info(session_id)
                            
                            if session_info and session_info.get('metadata'):
                                metadata = session_info['metadata']
                                original_audio_url = metadata.get('original_audio_url')
                                question_number = metadata.get('question_number')
                                submission_url = metadata.get('submission_url')
                                
                                if all([original_audio_url, question_number, submission_url]):
                                    # Trigger audio pipeline retry
                                    from app.pubsub.client import PubSubClient
                                    pubsub_client = PubSubClient()
                                    retry_message = {
                                        "audio_url": original_audio_url,
                                        "question_number": question_number,
                                        "submission_url": submission_url,
                                        "retry_reason": "pronunciation_file_not_found"
                                    }
                                    
                                    message_id = pubsub_client.publish_message_by_name(
                                        topic_name="STUDENT_SUBMISSION",
                                        message=retry_message
                                    )
                                    
                                    logger.info(f"Audio pipeline retry triggered with message ID: {message_id}")
                                    
                                    return {
                                        "grade": 0,
                                        "issues": [{
                                            "type": "retry",
                                            "message": f"Audio file not found after {max_wait_attempts} attempts. Pipeline retry initiated (Message ID: {message_id})"
                                        }]
                                    }
                        except Exception as retry_error:
                            logger.error(f"Failed to trigger audio pipeline retry: {str(retry_error)}")
                    
                    # Fallback if retry couldn't be triggered
                    raise FileNotFoundError(f"Audio file not found after {max_wait_attempts} attempts: {audio_file}")
            
            # Analyze transcript length and choose appropriate method
            word_count = len(reference_text.split())
            logger.info(f"Reference text has {word_count} words")
            
            # Choose analysis method based on transcript length (using 65-word limit)
            test_logs.take_memory_snapshot("method_selection", f"Selecting analysis method for {word_count} words")
            
            if word_count > 65:  # Long transcript - use chunking
                test_logs.log_workflow_step("analysis_method", "chunked_selected", f"Using chunked analysis for {word_count} words")
                logger.info("Using chunked analysis for long transcript")
                azure_result = await PronunciationService._analyze_with_chunking(audio_file, reference_text, test_logs)
            elif word_count > 15:  # Medium transcript - use extended timeout
                test_logs.log_workflow_step("analysis_method", "streaming_selected", f"Using streaming analysis for {word_count} words")
                logger.info("Using streaming analysis with extended timeout")
                azure_result = await PronunciationService._analyze_with_streaming(audio_file, reference_text)
            else:
                test_logs.log_workflow_step("analysis_method", "standard_selected", f"Using standard analysis for {word_count} words")
                logger.info("Using standard analysis for short transcript")
                azure_result = await PronunciationService._analyze_standard(audio_file, reference_text)
                
                # If standard fails, try extended as backup
                if azure_result is None:
                    logger.info("Standard analysis failed, trying streaming analysis as backup")
                    azure_result = await PronunciationService._analyze_with_streaming(audio_file, reference_text)
            
            # Process result based on recognition outcome
            if azure_result is None:
                # Mark service as complete even on error
                if session_id:
                    try:
                        file_manager_service = FileManagerService()
                        await file_manager_service.mark_service_complete(session_id, "pronunciation")
                    except Exception as e:
                        logger.warning(f"Failed to mark pronunciation service complete: {str(e)}")
                
                return {
                    "grade": 0,
                    "issues": [{"type": "suggestion", "message": "No pronunciation assessment result returned from Azure Speech Services."}]
                }
            
            logger.info("Speech recognized successfully")
            
            # Process the results using existing method
            processed_result = PronunciationService.process_pronunciation_result(azure_result, reference_text)
            
            # Add phrase chunking analysis
            phrase_chunks = PronunciationService.chunk_text_into_phrases(reference_text)
            processed_result["phrase_chunks"] = phrase_chunks
            processed_result["total_phrases"] = len(phrase_chunks)
            
            # Get improvement suggestion (now with phrase awareness)
            improvement_suggestion = await PronunciationService.get_improvement_suggestion(
                processed_result["transcript"],
                processed_result["critical_errors"],
                processed_result["filler_words"]
            )
            
            # Transform to standardized format
            standardized_result = PronunciationService._transform_to_standardized_format(
                processed_result, improvement_suggestion
            )
            
            # Mark service complete for proper file lifecycle management
            if session_id:
                try:
                    file_manager_service = FileManagerService()
                    await file_manager_service.mark_service_complete(session_id, "pronunciation")
                except Exception as e:
                    logger.warning(f"Failed to mark pronunciation service complete: {str(e)}")
            
            # Add test logs to result
            test_logs.take_memory_snapshot("analysis_complete", "All processing completed successfully")
            test_logs.log_workflow_step("pronunciation_analysis", "completed", "Analysis completed successfully")
            standardized_result["test_logs"] = test_logs.get_logs()
            
            return standardized_result
                
        except Exception as e:
            logger.exception("Error in analyze_pronunciation")
            
            # Log the error if test_logs is available
            if 'test_logs' in locals() and test_logs:
                test_logs.log_pronunciation_error("analysis_failed", f"Pronunciation analysis failed: {str(e)}", audio_file)
            
            # Mark service complete even on failure to prevent stuck sessions
            if session_id:
                try:
                    file_manager_service = FileManagerService()
                    await file_manager_service.mark_service_complete(session_id, "pronunciation")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to mark pronunciation service complete: {str(cleanup_error)}")
            
            error_result = {
                "grade": 0,
                "issues": [{"type": "suggestion", "message": str(e)}]
            }
            
            # Add test logs to error result if available
            if 'test_logs' in locals() and test_logs:
                error_result["test_logs"] = test_logs.get_logs()
            
            return error_result

    @staticmethod
    def process_pronunciation_result(azure_result, reference_text):
        """
        Process Azure Speech pronunciation assessment result
        
        Args:
            azure_result: Raw Azure pronunciation assessment result
            reference_text: Reference text
        """
        # Initialize result structure
        processed_result = {
            "status": "success",
            "audio_duration": azure_result.get("Duration", 0) / 10000000,  # Convert to seconds
            "transcript": reference_text,
            "azure_transcript": azure_result.get("DisplayText", ""),
            "overall_pronunciation_score": 0,
            "accuracy_score": 0,
            "fluency_score": 0,
            "prosody_score": 0,
            "completeness_score": 0,
            "critical_errors": [],
            "filler_words": [],
            "word_details": []
        }
        
        # Extract overall scores from NBest[0]
        if "NBest" in azure_result and azure_result["NBest"]:
            best_result = azure_result["NBest"][0]
            pronunciation_assessment = best_result.get("PronunciationAssessment", {})
            processed_result["overall_pronunciation_score"] = pronunciation_assessment.get("PronScore", 0)
            processed_result["accuracy_score"] = pronunciation_assessment.get("AccuracyScore", 0)
            processed_result["fluency_score"] = pronunciation_assessment.get("FluencyScore", 0)
            processed_result["prosody_score"] = pronunciation_assessment.get("ProsodyScore", 0)
            processed_result["completeness_score"] = pronunciation_assessment.get("CompletenessScore", 0)
        
        # Process word-level details
        if "NBest" in azure_result and azure_result["NBest"]:
            best_result = azure_result["NBest"][0]
            words = best_result.get("Words", [])
            
            # Track filler sounds and critical errors
            filler_pattern = re.compile(r'^(uh|um|uhh|uhm|er|erm|hmm)$', re.IGNORECASE)
            
            # Keywords to filter out
            filter_keywords = ["omission", "insertion"]
            
            for word in words:
                word_text = word.get("Word", "").lower()
                error_type = word.get("PronunciationAssessment", {}).get("ErrorType", "None")
                
                # Skip any entries containing the filter keywords in either word text or error type
                should_skip = False
                for keyword in filter_keywords:
                    if keyword in word_text.lower() or keyword in error_type.lower():
                        should_skip = True
                        break
                        
                if should_skip:
                    continue
                    
                assessment = word.get("PronunciationAssessment", {})
                accuracy_score = assessment.get("AccuracyScore", 0)
                

                
                # Convert timings from 100-nanosecond units to seconds
                offset_seconds = word.get("Offset", 0) / 10000000
                duration_seconds = word.get("Duration", 0) / 10000000
                
                # Add to word details
                word_detail = {
                    "word": word_text,
                    "offset": offset_seconds,
                    "duration": duration_seconds,
                    "accuracy_score": accuracy_score,
                    "error_type": error_type,
                    "reference_phonemes": PronunciationService.extract_reference_phonemes(word)[0],
                    "phoneme_details": PronunciationService.extract_reference_phonemes(word)[1]
                }
                
                processed_result["word_details"].append(word_detail)
                
                # Check for critical errors (accuracy score < 60)
                if accuracy_score < 60:
                    contains_filter_keyword = False
                    for keyword in filter_keywords:
                        if keyword in word_text.lower() or keyword in error_type.lower():
                            contains_filter_keyword = True
                            break
                    
                    if not contains_filter_keyword:
                        processed_result["critical_errors"].append({
                            "word": word_text,
                            "score": accuracy_score,
                            "timestamp": offset_seconds,
                            "duration": duration_seconds
                        })
                
                # Check for filler words/sounds
                if filler_pattern.match(word_text):
                    processed_result["filler_words"].append({
                        "word": word_text,
                        "timestamp": offset_seconds,
                        "duration": duration_seconds
                    })

        # Additional filter to ensure no filtered entries slip through
        filtered_critical_errors = []
        for error in processed_result["critical_errors"]:
            contains_filter_keyword = False
            for keyword in filter_keywords:
                if keyword in error["word"].lower():
                    contains_filter_keyword = True
                    break
            
            if not contains_filter_keyword:
                filtered_critical_errors.append(error)
        
        processed_result["critical_errors"] = filtered_critical_errors
        
        filtered_word_details = []
        for detail in processed_result["word_details"]:
            contains_filter_keyword = False
            for keyword in filter_keywords:
                if keyword in detail["word"].lower() or keyword in detail["error_type"].lower():
                    contains_filter_keyword = True
                    break
            
            if not contains_filter_keyword:
                filtered_word_details.append(detail)
        
        processed_result["word_details"] = filtered_word_details

        return processed_result

    @staticmethod
    async def get_improvement_suggestion(transcript: str, critical_errors: List[Dict], filler_words: List[Dict]) -> str:
        """
        Get a concise suggestion for pronunciation improvement using an LLM
        """
        if not OPENAI_API_KEY:
            # Fallback if no API key
            return PronunciationService.generate_fallback_suggestion(transcript, critical_errors, filler_words)
        
        try:
            # Prepare prompt for LLM
            error_info = ""
            if critical_errors:
                error_words = ", ".join([f"'{e['word']}' (score: {e['score']})" for e in critical_errors[:5]])
                error_info += f"Critical pronunciation errors: {error_words}. "
                
            if filler_words:
                filler_count = len(filler_words)
                filler_info = f"Used {filler_count} filler words/sounds. "
                error_info += filler_info
            
            prompt = f"""
            Based on a pronunciation assessment of the following speech:
            
            Transcript: "{transcript}"
            
            {error_info}
            
            Provide ONE CONCISE SENTENCE with actionable advice on how to improve pronunciation.
            Focus on the most critical issue. Be specific and direct.
            """
            
            # Call OpenAI API
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            }
            
            payload = {
                "model": "gpt-5-nano",
                "messages": [{"role": "user", "content": prompt}],
                "max_completion_tokens": 100,
                "temperature": 0.5
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(OPENAI_API_URL, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        suggestion = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        
                        # Clean up the suggestion if needed
                        suggestion = suggestion.strip().strip('"')
                        
                        # Ensure it's a single sentence
                        if "." in suggestion:
                            suggestion = suggestion.split(".")[0].strip() + "."
                            
                        return suggestion
                    else:
                        logger.error(f"OpenAI API error: {response.status}")
                        error_text = await response.text()
                        logger.error(f"Error details: {error_text}")
                        return PronunciationService.generate_fallback_suggestion(transcript, critical_errors, filler_words)
                        
        except Exception as e:
            logger.exception("Error getting improvement suggestion")
            return PronunciationService.generate_fallback_suggestion(transcript, critical_errors, filler_words)

    @staticmethod
    def generate_fallback_suggestion(transcript: str, critical_errors: List[Dict], filler_words: List[Dict]) -> str:
        """
        Generate a fallback suggestion without using an API
        """
        if len(critical_errors) > 3:
            error_words = ", ".join([f"'{e['word']}'" for e in critical_errors[:3]])
            return f"Focus on improving pronunciation of key words like {error_words}."
        
        elif len(filler_words) > 3:
            return "Reduce filler words by pausing silently instead of using sounds like 'uh' and 'um'."
        
        elif len(critical_errors) > 0:
            return f"Practice the correct pronunciation of '{critical_errors[0]['word']}' to improve clarity."
        
        elif not transcript:
            return "Speak more clearly and confidently to improve speech recognition."
        
        else:
            return "Continue practicing natural intonation and rhythm to sound more fluent."

    @staticmethod
    def _transform_to_standardized_format(processed_result: Dict[str, Any], improvement_suggestion: str) -> Dict[str, Any]:
        """Transform the processed Azure result to standardized format"""
        issues = []
        
        # Add word scores as the first issue if they exist and are configured to be an issue type
        # For now, word_details will be a top-level key in the response, not an "issue".
        # word_details = processed_result.get("word_details", [])
        # if word_details:
        #     words_data = []
        #     for word in word_details:
        #         words_data.append({
        #             "word": word.get("word", ""),
        #             "score": word.get("accuracy_score", 0),
        #             "duration": word.get("duration", 0),
        #             "timestamp": word.get("offset", 0),
        #             "error_type": word.get("error_type", "None"),
        #             "reference_phonemes": word.get("reference_phonemes", ""),
        #             "phoneme_details": word.get("phoneme_details", [])
        #         })
        #     issues.append({
        #         "type": "word_scores",
        #         "words": words_data
        #     })
        
        # Add improvement suggestion
        if improvement_suggestion:
            issues.append({
                "type": "suggestion",
                "message": improvement_suggestion
            })
        
        # Add prosody score as an issue if available (optional, can also be top-level)
        prosody_score = processed_result.get("prosody_score", 0)
        if prosody_score > 0:
            issues.append({
                "type": "prosody_feedback", # Renamed to avoid conflict if prosody_score is top-level
                "score": prosody_score,
                "message": "Work on natural rhythm and intonation patterns in speech."
            })
        
        # Add Azure's fluency score as an issue if available (optional, can also be top-level)
        # This is different from our WPM-based fluency service.
        azure_fluency_score = processed_result.get("fluency_score", 0)
        if azure_fluency_score > 0:
            issues.append({
                "type": "azure_fluency_feedback", # Renamed
                "score": azure_fluency_score,
                "message": "Focus on speaking more smoothly and reducing pauses between words (based on Azure's assessment)."
            })
        
        # Construct the final standardized result dictionary
        standardized_output = {
            "grade": processed_result.get("overall_pronunciation_score", 0),
            "accuracy_score": processed_result.get("accuracy_score", 0),
            "fluency_score": processed_result.get("fluency_score", 0), # Azure's fluency score
            "prosody_score": processed_result.get("prosody_score", 0),
            "completeness_score": processed_result.get("completeness_score", 0),
            "audio_duration": processed_result.get("audio_duration", 0.0),
            "word_details": processed_result.get("word_details", []),
            "critical_errors": processed_result.get("critical_errors", []),
            "filler_words": processed_result.get("filler_words", []),
            "transcript": processed_result.get("transcript", ""), # Original reference text
            "azure_transcript": processed_result.get("azure_transcript", ""), # Text recognized by Azure
            "issues": issues # Compiled list of textual feedback issues
        }
        
        # Note: phrase_chunks are used internally for analysis but not exposed in final response
        
        return standardized_output

    @staticmethod
    async def _analyze_standard(audio_file: str, reference_text: str):
        """Standard recognize_once implementation for short transcripts"""
        try:
            speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=REGION)
            audio_config = speechsdk.AudioConfig(filename=audio_file)
            
            pron_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True
            )
            
            recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            pron_config.apply_to(recognizer)
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, recognizer.recognize_once)
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                json_result = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
                if json_result:
                    return json.loads(json_result)
                    
            logger.warning(f"Standard analysis failed: {result.reason}")
            return None
            
        except Exception as e:
            logger.warning(f"Error in standard analysis: {str(e)}")
            return None

    @staticmethod 
    async def _analyze_with_streaming(audio_file: str, reference_text: str):
        """Extended recognition with longer timeouts for medium transcripts"""
        try:
            speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=REGION)
            
            # Configure for longer audio processing
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "30000")
            speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "30000")
            speech_config.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "2000")
            speech_config.request_word_level_timestamps()
            
            audio_config = speechsdk.AudioConfig(filename=audio_file)
            
            pron_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True
            )
            
            recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            pron_config.apply_to(recognizer)
            
            logger.info(f"Starting extended pronunciation assessment with {len(reference_text.split())} words")
            
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, recognizer.recognize_once)
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                json_result = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
                if json_result:
                    logger.info("Extended pronunciation analysis completed")
                    return json.loads(json_result)
                    
            logger.warning(f"Streaming analysis failed: {result.reason}")
            return None
            
        except Exception as e:
            logger.warning(f"Error in streaming analysis: {str(e)}")
            return None

    @staticmethod
    async def _analyze_with_chunking(audio_file: str, reference_text: str, test_logs: Optional[TestLogsManager] = None):
        """Chunked pronunciation analysis for long transcripts (>65 words)"""
        try:
            import subprocess
            import os
            
            # Initialize test logs if not provided
            if test_logs is None:
                test_logs = TestLogsManager()
            
            test_logs.log_processing_step("chunked_analysis_start", "started", f"Text length: {len(reference_text)} chars")
            
            # Memory monitoring (optional)
            try:
                import psutil
                process = psutil.Process(os.getpid())
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_limit = 900  # MB (under 1024 MB Cloud Run limit)
                memory_monitoring = True
                test_logs.log_processing_step("memory_monitoring", "enabled", f"Initial: {initial_memory:.1f} MB, Limit: {memory_limit} MB")
                logger.info(f"Memory monitoring enabled. Initial usage: {initial_memory:.1f} MB")
            except (ImportError, Exception) as e:
                test_logs.log_memory_error("monitoring_setup_failed", f"Could not enable memory monitoring: {str(e)}")
                logger.debug(f"Memory monitoring disabled: {e}")
                memory_monitoring = False
                initial_memory = 0
                memory_limit = float('inf')
                process = None
            
            logger.info(f"Starting chunked pronunciation analysis with {len(reference_text.split())} words")
            
            # Split reference text into chunks (40 words each, based on 65-word limit)
            words = reference_text.split()
            chunk_size = 40
            text_chunks = []
            
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunk_text = " ".join(chunk_words)
                text_chunks.append({
                    "text": chunk_text,
                    "start_word": i,
                    "end_word": min(i + chunk_size, len(words)),
                    "word_count": len(chunk_words)
                })
            
            logger.info(f"Split into {len(text_chunks)} chunks")
            
            # Get audio duration
            try:
                cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
                       '-of', 'csv=p=0', audio_file]
                result = subprocess.run(cmd, capture_output=True, text=True)
                total_duration = float(result.stdout.strip())
                logger.info(f"Total audio duration: {total_duration:.1f} seconds")
            except Exception as e:
                logger.warning(f"Could not get audio duration: {e}, using estimated timing")
                total_duration = len(words) * 0.6  # Estimate ~0.6 seconds per word
            
            # No longer using fixed chunk duration - using word-based timing instead
            
            # Process each chunk with accurate timestamp tracking
            all_results = []
            combined_words = []
            cumulative_words_processed = 0
            
            for i, chunk in enumerate(text_chunks):
                logger.info(f"Processing chunk {i+1}/{len(text_chunks)}: {chunk['word_count']} words")
                
                # Calculate time range for this chunk based on word position
                # More accurate: estimate time based on word position rather than equal splits
                words_per_second = len(words) / total_duration if total_duration > 0 else 1.5  # fallback rate
                chunk_start_time = cumulative_words_processed / words_per_second
                estimated_chunk_duration = chunk['word_count'] / words_per_second
                
                logger.info(f"   Chunk timing: start={chunk_start_time:.2f}s, duration={estimated_chunk_duration:.2f}s")
                
                # Create temporary audio chunk using context manager
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                    temp_chunk_file = temp_file.name
                
                try:
                    cmd = [
                        'ffmpeg', '-y', '-i', audio_file,
                        '-ss', str(chunk_start_time), '-t', str(estimated_chunk_duration + 1.0),  # Add 1s buffer
                        '-c', 'copy', temp_chunk_file
                    ]
                    
                    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if result.returncode != 0:
                        logger.warning(f"Failed to extract audio chunk {i+1}")
                        cumulative_words_processed += chunk['word_count']
                        continue
                    
                    # Process this chunk with standard analysis
                    chunk_result = await PronunciationService._analyze_standard(temp_chunk_file, chunk['text'])
                    
                    if chunk_result:
                        logger.info(f"Chunk {i+1} processed successfully")
                        
                        # Extract words and adjust their timestamps accurately
                        if "NBest" in chunk_result and chunk_result["NBest"]:
                            chunk_words = chunk_result["NBest"][0].get("Words", [])
                            
                            for word_data in chunk_words:
                                # Calculate accurate global timestamp
                                # Original offset from chunk + chunk start time in global audio
                                original_offset_seconds = word_data.get("Offset", 0) / 10000000  # Convert to seconds
                                global_offset_seconds = chunk_start_time + original_offset_seconds
                                
                                # Update with accurate global timestamp
                                word_data["Offset"] = int(global_offset_seconds * 10000000)  # Convert back to 100-nanosecond units
                                
                                combined_words.append(word_data)
                        
                        # Extract only essential data to reduce memory usage
                        essential_chunk_data = {
                            "scores": {
                                "PronScore": chunk_result["NBest"][0].get("PronunciationAssessment", {}).get("PronScore", 0) if "NBest" in chunk_result and chunk_result["NBest"] else 0,
                                "AccuracyScore": chunk_result["NBest"][0].get("PronunciationAssessment", {}).get("AccuracyScore", 0) if "NBest" in chunk_result and chunk_result["NBest"] else 0,
                                "FluencyScore": chunk_result["NBest"][0].get("PronunciationAssessment", {}).get("FluencyScore", 0) if "NBest" in chunk_result and chunk_result["NBest"] else 0
                            },
                            "valid": True
                        }
                        all_results.append(essential_chunk_data)
                        logger.info(f"   Added {len(chunk_words)} words with timestamps starting at {chunk_start_time:.2f}s")
                        
                        # Clear chunk_result to free memory immediately
                        del chunk_result
                        del chunk_words
                    else:
                        logger.warning(f"Chunk {i+1} failed to process")
                        all_results.append({"valid": False})
                
                finally:
                    # Clean up temporary file with proper error logging
                    if os.path.exists(temp_chunk_file):
                        try:
                            os.unlink(temp_chunk_file)
                            logger.debug(f"Successfully cleaned up temporary chunk file: {temp_chunk_file}")
                        except OSError as e:
                            logger.warning(f"Failed to cleanup temporary chunk file {temp_chunk_file}: {e}")
                        except Exception as e:
                            logger.error(f"Unexpected error cleaning up chunk file {temp_chunk_file}: {e}")
                
                # Progressive cleanup and garbage collection for large datasets
                if (i + 1) % 3 == 0 or len(combined_words) > 500:  # Every 3 chunks or 500+ words
                    import gc
                    gc.collect()
                    
                    # Memory monitoring and circuit breaker
                    if memory_monitoring and process:
                        current_memory = process.memory_info().rss / 1024 / 1024  # MB
                        logger.debug(f"Performed garbage collection after chunk {i+1}. Memory: {current_memory:.1f} MB")
                        
                        if current_memory > memory_limit:
                            test_logs.log_memory_error("memory_limit_exceeded", f"Memory limit exceeded: {current_memory:.1f} MB > {memory_limit} MB. Stopping chunked analysis at chunk {i+1}.", current_memory)
                            logger.warning(f"Memory limit exceeded ({current_memory:.1f} MB > {memory_limit} MB). Stopping chunked analysis.")
                            # Return partial results
                            break
                    else:
                        logger.debug(f"Performed garbage collection after chunk {i+1}")
                
                # Update cumulative count for next chunk
                cumulative_words_processed += chunk['word_count']
            
            # Combine results
            if all_results:
                logger.info(f"Combining {len(all_results)} chunk results")
                
                # Calculate overall scores (average of chunk scores)
                total_pron_score = 0
                total_accuracy_score = 0
                total_fluency_score = 0
                valid_chunks = 0
                
                for chunk_data in all_results:
                    if chunk_data.get("valid", False):
                        scores = chunk_data.get("scores", {})
                        total_pron_score += scores.get("PronScore", 0)
                        total_accuracy_score += scores.get("AccuracyScore", 0)
                        total_fluency_score += scores.get("FluencyScore", 0)
                        valid_chunks += 1
                
                if valid_chunks > 0:
                    avg_pron_score = total_pron_score / valid_chunks
                    avg_accuracy_score = total_accuracy_score / valid_chunks
                    avg_fluency_score = total_fluency_score / valid_chunks
                else:
                    avg_pron_score = avg_accuracy_score = avg_fluency_score = 0
                
                # Create combined result
                combined_result = {
                    "Duration": int(total_duration * 10000000),  # Convert to 100-nanosecond units
                    "DisplayText": " ".join([chunk["text"] for chunk in text_chunks]),
                    "NBest": [{
                        "PronunciationAssessment": {
                            "PronScore": avg_pron_score,
                            "AccuracyScore": avg_accuracy_score,
                            "FluencyScore": avg_fluency_score,
                            "CompletenessScore": 100  # Assume complete
                        },
                        "Words": combined_words
                    }]
                }
                
                logger.info(f"Chunked analysis completed! Combined scores - Pronunciation: {avg_pron_score:.1f}, Accuracy: {avg_accuracy_score:.1f}, Fluency: {avg_fluency_score:.1f}")
                logger.info(f"Total words processed: {len(combined_words)}")
                
                # Final memory check
                if memory_monitoring and process:
                    final_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_used = final_memory - initial_memory
                    logger.info(f"Memory usage: {final_memory:.1f} MB (Δ{memory_used:+.1f} MB)")
                
                # Final cleanup for large datasets
                del all_results
                del text_chunks
                import gc
                gc.collect()
                logger.debug("Final garbage collection completed for chunked analysis")
                
                return combined_result
            else:
                logger.warning("No chunks processed successfully")
                
                # Cleanup even on failure
                del all_results
                del combined_words
                import gc
                gc.collect()
                
                return None
                
        except Exception as e:
            logger.warning(f"Error in chunked analysis: {str(e)}")
            return None