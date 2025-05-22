import os
import logging
import aiohttp
import asyncio
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
ASSEMBLYAI_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "793e69da37b04250a9473ff974eb7157")
ASSEMBLYAI_UPLOAD_URL = "https://api.assemblyai.com/v2/upload"
ASSEMBLYAI_TRANSCRIPT_URL = "https://api.assemblyai.com/v2/transcript"

class TranscriptionService:
    """Service for handling audio transcription"""
    
    @staticmethod
    async def upload_to_assemblyai(file_path: str) -> str:
        """Upload audio file to AssemblyAI"""
        logger.info(f"Uploading file to AssemblyAI: {file_path}")
        
        headers = {"authorization": ASSEMBLYAI_API_KEY}
        
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
    
    @staticmethod
    async def get_assemblyai_transcript(audio_url: str) -> Dict[str, Any]:
        """Get transcript from AssemblyAI"""
        headers = {
            "authorization": ASSEMBLYAI_API_KEY,
            "content-type": "application/json"
        }
        
        data = {
            "audio_url": audio_url,
            "speaker_labels": True,
            "punctuate": True,
            "format_text": True
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Submit transcription request
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
                    
                    # Poll for completion
                    polling_endpoint = f"{ASSEMBLYAI_TRANSCRIPT_URL}/{transcript_id}"
                    
                    while True:
                        await asyncio.sleep(3)
                        
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
    
    @staticmethod
    async def transcribe_audio_from_url(audio_url: str) -> Dict[str, Any]:
        """Main transcription function for URL"""
        try:
            # Transcribe directly from URL (no need to upload since we already have a URL)
            transcript_result = await TranscriptionService.get_assemblyai_transcript(audio_url)
            
            transcript_text = transcript_result.get('text', '')
            
            if not transcript_text:
                return {
                    "text": "",
                    "error": "AssemblyAI returned empty transcript"
                }
            
            logger.info(f"Transcription successful: {transcript_text}")
            return {
                "text": transcript_text,
                "error": None
            }
            
        except Exception as e:
            logger.exception(f"Error in transcribe_audio_from_url: {str(e)}")
            return {
                "text": "",
                "error": str(e)
            }