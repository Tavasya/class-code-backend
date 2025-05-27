import azure.cognitiveservices.speech as speechsdk
import json
import os
import logging
from typing import Dict, List, Any, Tuple
import aiohttp
import re
import subprocess
import tempfile
import asyncio
import time

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Azure Speech config - retrieve from environment variables for security
SPEECH_KEY = os.environ.get("AZURE_SPEECH_KEY", "CA4BV9f9rvEKQL22h6L383ucFVNHl9HvkS9bYsBR8xI6cdJm85fHJQQJ99BEACYeBjFXJ3w3AAAYACOGS9sl")
REGION = os.environ.get("AZURE_SPEECH_REGION", "eastus")

# AssemblyAI API config
ASSEMBLYAI_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY")
if not ASSEMBLYAI_API_KEY:
    logger.error("ASSEMBLYAI_API_KEY environment variable is not set")
    raise ValueError("ASSEMBLYAI_API_KEY environment variable is required")
ASSEMBLYAI_UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
ASSEMBLYAI_TRANSCRIPT_URL = "https://api.assemblyai.com/v2/transcript"

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

async def upload_to_assemblyai(file_path: str) -> str:
    """
    Upload an audio file to AssemblyAI
    
    Args:
        file_path: Path to the audio file
        
    Returns:
        The URL of the uploaded file on AssemblyAI's servers
    """
    logger.info(f"Uploading file to AssemblyAI: {file_path}")
    
    headers = {
        "authorization": ASSEMBLYAI_API_KEY
    }
    
    try:
        with open(file_path, 'rb') as audio_file:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    ASSEMBLYAI_UPLOAD_URL,
                    headers=headers,
                    data=audio_file
                ) as response:
                    if response.status == 200:
                        response_json = await response.json()
                        upload_url = response_json.get('upload_url')
                        logger.info(f"File uploaded successfully: {upload_url}")
                        return upload_url
                    else:
                        error_text = await response.text()
                        logger.error(f"AssemblyAI upload error: {response.status}, {error_text}")
                        raise Exception(f"AssemblyAI upload failed: {error_text}")
    
    except Exception as e:
        logger.exception("Error uploading to AssemblyAI")
        raise Exception(f"Failed to upload file to AssemblyAI: {str(e)}")

async def get_assemblyai_transcript(audio_url: str) -> Dict[str, Any]:
    """
    Submit and retrieve a transcript from AssemblyAI
    
    Args:
        audio_url: URL of the uploaded audio file
        
    Returns:
        The transcript and related data
    """
    headers = {
        "authorization": ASSEMBLYAI_API_KEY,
        "content-type": "application/json"
    }
    
    # Request body for the transcript
    data = {
        "audio_url": audio_url,
        "speaker_labels": True,  # Optional: identify different speakers
        "punctuate": True,
        "format_text": True
    }
    
    try:
        # Submit the transcription request
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ASSEMBLYAI_TRANSCRIPT_URL,
                json=data,
                headers=headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"AssemblyAI transcription request error: {response.status}, {error_text}")
                    raise Exception(f"AssemblyAI transcription request failed: {error_text}")
                
                transcript_response = await response.json()
                transcript_id = transcript_response['id']
                logger.info(f"Transcription request submitted: {transcript_id}")
                
                # Poll for the transcript completion
                polling_endpoint = f"{ASSEMBLYAI_TRANSCRIPT_URL}/{transcript_id}"
                
                while True:
                    await asyncio.sleep(3)  # Poll every 3 seconds
                    
                    async with session.get(polling_endpoint, headers=headers) as polling_response:
                        if polling_response.status != 200:
                            error_text = await polling_response.text()
                            logger.error(f"AssemblyAI polling error: {polling_response.status}, {error_text}")
                            raise Exception(f"AssemblyAI polling failed: {error_text}")
                        
                        polling_result = await polling_response.json()
                        status = polling_result['status']
                        
                        if status == 'completed':
                            logger.info(f"Transcription completed: {transcript_id}")
                            return polling_result
                        elif status == 'error':
                            error_message = polling_result.get('error', 'Unknown error')
                            logger.error(f"AssemblyAI transcription error: {error_message}")
                            raise Exception(f"AssemblyAI transcription failed: {error_message}")
                        
                        logger.info(f"Transcription in progress: {status}")
    
    except Exception as e:
        logger.exception("Error getting transcript from AssemblyAI")
        raise Exception(f"Failed to get transcript from AssemblyAI: {str(e)}")

async def analyze_audio_file(audio_file: str) -> Dict[str, Any]:
    """
    Process an audio file using AssemblyAI for transcription and Azure for pronunciation assessment
    
    Args:
        audio_file: Path to the audio file
        
    Returns:
        Pronunciation analysis results with transcript from AssemblyAI
    """
    temp_wav_file = None
    
    try:
        # Check if the file is WebM and convert if needed
        if audio_file.lower().endswith('.webm'):
            logger.info(f"Detected WebM file, converting: {audio_file}")
            temp_wav_file = await convert_webm_to_wav(audio_file)
            file_to_process = temp_wav_file
        else:
            file_to_process = audio_file
        
        # Step 1: Upload to AssemblyAI and get transcript
        upload_url = await upload_to_assemblyai(file_to_process)
        transcript_result = await get_assemblyai_transcript(upload_url)
        
        # Extract transcript text
        transcript_text = transcript_result.get('text', '')
        
        if not transcript_text:
            return {
                "status": "error",
                "error": "AssemblyAI returned empty transcript",
                "transcript": ""
            }
        
        logger.info(f"AssemblyAI transcript: {transcript_text}")
        
        # Step 2: Use Azure for pronunciation assessment with the AssemblyAI transcript
        pronunciation_result = await analyze_pronunciation(file_to_process, transcript_text)
        
        # Add AssemblyAI detailed data to the result
        pronunciation_result["assemblyai_data"] = {
            "words": transcript_result.get("words", []),
            "utterances": transcript_result.get("utterances", []),
            "confidence": transcript_result.get("confidence")
        }
        
        return pronunciation_result
        
    except Exception as e:
        logger.exception(f"Error in analyze_audio_file: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "transcript": ""
        }
        
    finally:
        # Clean up temporary WAV file if created
        if temp_wav_file and os.path.exists(temp_wav_file):
            try:
                os.unlink(temp_wav_file)
                logger.info(f"Cleaned up temporary file: {temp_wav_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_wav_file}: {str(e)}")

async def analyze_pronunciation(audio_file: str, reference_text: str) -> Dict[str, Any]:
    """
    Analyze pronunciation using Azure Speech Services with a provided reference text
    
    Args:
        audio_file: Path to the audio file
        reference_text: Transcript text from AssemblyAI to use as reference
        
    Returns:
        Pronunciation assessment results
    """
    try:
        # Set up the Speech config
        speech_config = speechsdk.SpeechConfig(subscription=SPEECH_KEY, region=REGION)
        audio_config = speechsdk.AudioConfig(filename=audio_file)
        
        # Configure pronunciation assessment with the AssemblyAI reference text
        pron_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,  # Use transcript from AssemblyAI
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
        logger.info(f"Starting pronunciation assessment on {audio_file} with reference text")
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
                    "transcript": reference_text  # Use AssemblyAI transcript
                }
            
            # Parse the JSON result
            azure_result = json.loads(json_result)
            
            # Process the results
            processed_result = process_pronunciation_result(azure_result, reference_text)
            
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
                "transcript": reference_text  # Use AssemblyAI transcript
            }
            
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation = result.cancellation_details
            logger.error(f"Speech recognition canceled: {cancellation.reason}")
            if cancellation.reason == speechsdk.CancellationReason.Error:
                logger.error(f"Error details: {cancellation.error_details}")
            
            return {
                "status": "error",
                "error": f"Recognition canceled: {cancellation.reason}, {cancellation.error_details if hasattr(cancellation, 'error_details') else ''}",
                "transcript": reference_text  # Use AssemblyAI transcript
            }
            
    except Exception as e:
        logger.exception("Error in analyze_pronunciation")
        return {
            "status": "error",
            "error": str(e),
            "transcript": reference_text  # Use AssemblyAI transcript
        }

def process_pronunciation_result(azure_result, reference_text):
    """
    Process Azure Speech pronunciation assessment result with AssemblyAI transcript
    
    Args:
        azure_result: Raw Azure pronunciation assessment result
        reference_text: Reference text from AssemblyAI
    """
    # Initialize result structure with the AssemblyAI transcript
    processed_result = {
        "status": "success",
        "audio_duration": azure_result.get("Duration", 0) / 10000000,  # Convert to seconds
        "transcript": reference_text,  # Use AssemblyAI transcript
        "azure_transcript": azure_result.get("DisplayText", ""),  # Still keep Azure's transcript
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
                "error_type": error_type
            }
            
            processed_result["word_details"].append(word_detail)
            
            # Check for critical errors (accuracy score < 60)
            # Also make sure this doesn't contain any filtered keywords
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