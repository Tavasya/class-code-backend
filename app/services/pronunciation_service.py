import os
import json
import logging
import re
import aiohttp
import tempfile
import azure.cognitiveservices.speech as speechsdk
from typing import Dict, List, Any, Optional
from app.core.config import OPENAI_API_KEY, AZURE_SPEECH_KEY, AZURE_SPEECH_REGION, OPENAI_API_URL
from app.services.file_manager_service import file_manager
import unicodedata

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure Speech config
SPEECH_KEY = AZURE_SPEECH_KEY
REGION = AZURE_SPEECH_REGION

# OpenAI API config for improvement suggestions
OPENAI_URL = OPENAI_API_URL

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
        """Extract reference phonemes from Azure word data"""
        phonemes = word_data.get("Phonemes", [])
        if not phonemes:
            return "", []
        
        # Extract the phoneme names and join them
        phoneme_list = []
        phoneme_details = []
        
        for phoneme_data in phonemes:
            # Get the phoneme and ensure it's properly decoded as UTF-8
            phoneme = phoneme_data.get("Phoneme", "")
            if isinstance(phoneme, bytes):
                phoneme = phoneme.decode('utf-8')
            elif isinstance(phoneme, str):
                # Get stress information directly from the phoneme data
                stress = phoneme_data.get("Stress", 0)  # 0 = no stress, 1 = primary, 2 = secondary
                
                # Convert Azure phoneme to IPA
                phoneme = PronunciationService.convert_to_ipa(phoneme)
                
                # Add stress markers based on the stress field
                if stress == 1:
                    phoneme = "ˈ" + phoneme  # Primary stress
                elif stress == 2:
                    phoneme = "ˌ" + phoneme  # Secondary stress
                
                phoneme = unicodedata.normalize('NFC', phoneme)
            
            if phoneme:
                phoneme_list.append(phoneme)
                # Add detailed phoneme information including stress
                phoneme_details.append({
                    "phoneme": phoneme,
                    "accuracy_score": phoneme_data.get("PronunciationAssessment", {}).get("AccuracyScore", 0),
                    "error_type": phoneme_data.get("PronunciationAssessment", {}).get("ErrorType", "None"),
                    "stress": phoneme_data.get("Stress", 0)  # Include stress level in details
                })
        
        # Return as IPA string format with stress marks and detailed phoneme list
        if phoneme_list:
            # Ensure the final string is properly normalized
            ipa_string = "/" + "".join(phoneme_list) + "/"
            ipa_string = unicodedata.normalize('NFC', ipa_string)
            return ipa_string, phoneme_details
        
        return "", []
    #
    @staticmethod
    async def analyze_pronunciation(audio_file: str, reference_text: str, session_id: Optional[str] = None) -> Dict[str, Any]:
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
            # Validate that we have a local file path, not a URL
            if audio_file.startswith(('http://', 'https://')):
                raise ValueError("PronunciationService now only accepts local file paths, not URLs. "
                               "Audio URLs should be converted to local files by AudioService first.")
            
            # Verify file exists
            if not os.path.exists(audio_file):
                raise FileNotFoundError(f"Audio file not found: {audio_file}")
            
            # Set up the Speech config
            speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=REGION)
            audio_config = speechsdk.AudioConfig(filename=audio_file)
            
            # Configure pronunciation assessment with the reference text
            pron_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True
            )
            
            # Create recognizer
            recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            pron_config.apply_to(recognizer)
            
            # Run recognition
            logger.info(f"Starting pronunciation assessment on {audio_file} with reference text")
            result = recognizer.recognize_once()
            
            # Process result based on recognition outcome
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                logger.info("Speech recognized successfully")
                
                # Get the detailed JSON result
                json_result = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
                
                if not json_result:
                    # Mark service as complete even on error
                    if session_id:
                        try:
                            await file_manager.mark_service_complete(session_id, "pronunciation")
                        except Exception as e:
                            logger.warning(f"Failed to mark pronunciation service complete: {str(e)}")
                    
                    return {
                        "grade": 0,
                        "issues": [{"type": "suggestion", "message": "No pronunciation assessment result returned from Azure Speech Services."}]
                    }
                
                # Parse the JSON result
                azure_result = json.loads(json_result)
                
                # Process the results using existing method
                processed_result = PronunciationService.process_pronunciation_result(azure_result, reference_text)
                
                # Get improvement suggestion
                improvement_suggestion = await PronunciationService.get_improvement_suggestion(
                    processed_result["transcript"],
                    processed_result["critical_errors"],
                    processed_result["filler_words"]
                )
                
                # Transform to standardized format
                standardized_result = PronunciationService._transform_to_standardized_format(
                    processed_result, improvement_suggestion
                )
                
                # Mark pronunciation service as complete for this session
                if session_id:
                    try:
                        await file_manager.mark_service_complete(session_id, "pronunciation")
                        logger.info(f"Marked pronunciation service complete for session {session_id}")
                    except Exception as e:
                        logger.warning(f"Failed to mark pronunciation service complete for session {session_id}: {str(e)}")
                
                return standardized_result
                
            elif result.reason == speechsdk.ResultReason.NoMatch:
                logger.warning(f"No speech recognized: {result.no_match_details}")
                # Still mark service as complete even if no match
                if session_id:
                    try:
                        await file_manager.mark_service_complete(session_id, "pronunciation")
                    except Exception as e:
                        logger.warning(f"Failed to mark pronunciation service complete: {str(e)}")
                
                return {
                    "grade": 0,
                    "issues": [{"type": "suggestion", "message": f"No speech recognized: {result.no_match_details.reason}"}]
                }
                
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                logger.error(f"Speech recognition canceled: {cancellation.reason}")
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"Error details: {cancellation.error_details}")
                
                # Mark service as complete even on error
                if session_id:
                    try:
                        await file_manager.mark_service_complete(session_id, "pronunciation")
                    except Exception as e:
                        logger.warning(f"Failed to mark pronunciation service complete: {str(e)}")
                
                error_msg = f"Recognition canceled: {cancellation.reason}"
                if hasattr(cancellation, 'error_details'):
                    error_msg += f", {cancellation.error_details}"
                
                return {
                    "grade": 0,
                    "issues": [{"type": "suggestion", "message": error_msg}]
                }
                
        except Exception as e:
            logger.exception("Error in analyze_pronunciation")
            
            # Mark service as complete even on error to prevent hanging
            if session_id:
                try:
                    await file_manager.mark_service_complete(session_id, "pronunciation")
                except Exception as cleanup_error:
                    logger.warning(f"Failed to mark pronunciation service complete: {str(cleanup_error)}")
            
            return {
                "grade": 0,
                "issues": [{"type": "suggestion", "message": str(e)}]
            }

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
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
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
        
        return standardized_output