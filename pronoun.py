import azure.cognitiveservices.speech as speechsdk
import json
import os
import logging
from typing import Dict, List, Any, Tuple
import aiohttp
import re
import subprocess
import tempfile

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure Speech config - retrieve from environment variables for security
SPEECH_KEY = os.environ.get("AZURE_SPEECH_KEY", "CPhzqHVeoa5YnFTLqimhoVB8tiM0aYdtnAnumfNJtVkv3AzHV18PJQQJ99BDACYeBjFXJ3w3AAAYACOGaN2q")
REGION = os.environ.get("AZURE_SPEECH_REGION", "eastus")

# OpenAI API config for improvement suggestions
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "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")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

async def convert_webm_to_wav(webm_file: str) -> str:
    """
    Convert WebM audio to WAV format for Azure Speech Service compatibility
    
    Args:
        webm_file: Path to the WebM file
        
    Returns:
        Path to the converted WAV file
    """
    # Create output filename in the same directory
    wav_file = os.path.splitext(webm_file)[0] + '.wav'
    
    logger.info(f"Converting {webm_file} to {wav_file}")
    
    try:
        # Run ffmpeg to convert WebM to WAV (PCM 16-bit, 16kHz, mono)
        command = [
            'ffmpeg',
            '-i', webm_file,        # Input file
            '-acodec', 'pcm_s16le',  # Output codec (16-bit PCM)
            '-ar', '16000',          # Sample rate (16kHz)
            '-ac', '1',              # Channels (mono)
            '-y',                    # Overwrite output file if it exists
            wav_file                 # Output file
        ]
        
        # Execute ffmpeg command
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        
        logger.info(f"Conversion successful: {wav_file}")
        return wav_file
    
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg conversion failed: {e.stderr.decode()}")
        raise Exception(f"Failed to convert WebM to WAV: {e.stderr.decode()}")
    
    except Exception as e:
        logger.error(f"Error in conversion: {str(e)}")
        raise Exception(f"Error converting WebM to WAV: {str(e)}")

async def analyze_audio_file(audio_file: str) -> Dict[str, Any]:
    """
    Process an audio file, handling WebM conversion if needed
    
    Args:
        audio_file: Path to the audio file
        
    Returns:
        Pronunciation analysis results
    """
    temp_wav_file = None
    
    try:
        # Check if the file is WebM and convert if needed
        if audio_file.lower().endswith('.webm'):
            logger.info(f"Detected WebM file, converting: {audio_file}")
            temp_wav_file = await convert_webm_to_wav(audio_file)
            result = await analyze_pronunciation(temp_wav_file)
        else:
            # Directly analyze WAV files
            result = await analyze_pronunciation(audio_file)
            
        return result
        
    finally:
        # Clean up temporary WAV file if created
        if temp_wav_file and os.path.exists(temp_wav_file):
            try:
                os.unlink(temp_wav_file)
                logger.info(f"Cleaned up temporary file: {temp_wav_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_wav_file}: {str(e)}")

async def analyze_pronunciation(audio_file: str) -> Dict[str, Any]:
    """
    Analyze pronunciation using Azure Speech Services
    """
    try:
        # Set up the Speech config
        speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=REGION)
        audio_config = speechsdk.AudioConfig(filename=audio_file)
        
        # Configure pronunciation assessment
        pron_config = speechsdk.PronunciationAssessmentConfig(
            reference_text="",  # Empty for unscripted assessment
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True
        )
        pron_config.phoneme_alphabet = "IPA"
        pron_config.enable_prosody_assessment()
        pron_config.n_best_phoneme_count = 5
        
        # Create recognizer
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        pron_config.apply_to(recognizer)
        
        # Run recognition
        logger.info(f"Starting speech recognition on {audio_file}")
        result = recognizer.recognize_once()
        
        # Process result based on recognition outcome
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            logger.info("Speech recognized successfully")
            
            # Get the detailed JSON result
            json_result = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
            
            if not json_result:
                return {
                    "status": "error",
                    "error": "No pronunciation assessment result returned",
                    "transcript": result.text
                }
            
            # Parse the JSON result
            azure_result = json.loads(json_result)
            
            # Process the results
            processed_result = process_pronunciation_result(azure_result)
            
            # Get improvement suggestion
            improvement_suggestion = await get_improvement_suggestion(
                processed_result["transcript"],
                processed_result["critical_errors"],
                processed_result["filler_words"]
            )
            
            processed_result["improvement_suggestion"] = improvement_suggestion
            return processed_result
            
        elif result.reason == speechsdk.ResultReason.NoMatch:
            logger.warning(f"No speech recognized: {result.no_match_details}")
            return {
                "status": "error",
                "error": f"No speech recognized: {result.no_match_details.reason}",
                "transcript": ""
            }
            
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            logger.error(f"Speech recognition canceled: {cancellation.reason}")
            if cancellation.reason == speechsdk.CancellationReason.Error:
                logger.error(f"Error details: {cancellation.error_details}")
            
            return {
                "status": "error",
                "error": f"Recognition canceled: {cancellation.reason}, {cancellation.error_details if hasattr(cancellation, 'error_details') else ''}",
                "transcript": ""
            }
            
    except Exception as e:
        logger.exception("Error in analyze_pronunciation")
        return {
            "status": "error",
            "error": str(e),
            "transcript": ""
        }

def process_pronunciation_result(azure_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process Azure Speech pronunciation assessment result
    """
    # Extract transcript
    transcript = azure_result.get("DisplayText", "")
    
    # Initialize result structure
    processed_result = {
        "status": "success",
        "audio_duration": azure_result.get("Duration", 0) / 10000000,  # Convert to seconds
        "transcript": transcript,
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

        
        for word in words:
            word_text = word.get("Word", "").lower()
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
                "error_type": assessment.get("ErrorType", "None")
            }
            
            processed_result["word_details"].append(word_detail)
            
            # Check for critical errors (accuracy score < 60)
            if accuracy_score < 60:
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
    
    
    logger.info(f"Raw Azure result: {json.dumps(azure_result, indent=2)}")
    return processed_result

async def get_improvement_suggestion(transcript: str, critical_errors: List[Dict], filler_words: List[Dict]) -> str:
    """
    Get a concise suggestion for pronunciation improvement using an LLM
    """
    if not OPENAI_API_KEY:
        # Fallback if no API key
        return generate_fallback_suggestion(transcript, critical_errors, filler_words)
    
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
                    return generate_fallback_suggestion(transcript, critical_errors, filler_words)
                    
    except Exception as e:
        logger.exception("Error getting improvement suggestion")
        return generate_fallback_suggestion(transcript, critical_errors, filler_words)

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