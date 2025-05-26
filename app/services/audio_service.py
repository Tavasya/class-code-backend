import os
import aiohttp
import tempfile
import subprocess
import logging
from app.services.file_manager_service import file_manager

logger = logging.getLogger(__name__)

class AudioService:
    def __init__(self):
        pass

    async def process_single_audio(self, audio_url: str, question_number: int, submission_url: str) -> dict:
        """Process a single audio URL with centralized file management"""
        try:
            # Generate session ID for this file
            session_id = file_manager.generate_session_id(submission_url, question_number)
            
            # Download and convert audio
            wav_path = await self.convert_to_wav(audio_url)
            
            # Register file with dependencies (pronunciation service will use this file)
            dependent_services = {"pronunciation"}  # Only pronunciation service needs the converted file
            await file_manager.register_file_session(
                session_id=session_id,
                file_path=wav_path,
                dependent_services=dependent_services,
                cleanup_timeout_minutes=30  # Cleanup after 30 minutes if services don't complete
            )
            
            return {
                "wav_path": wav_path,
                "session_id": session_id,
                "question_number": question_number
            }
        except Exception as e:
            logger.error(f"Error processing audio URL {audio_url} for question {question_number}: {str(e)}")
            raise

    async def convert_to_wav(self, audio_url: str) -> str:
        """Download audio from URL and convert to WAV for speech analysis"""
        # Download from URL
        file_path = await self.download_audio(audio_url)
        
        try:
            # Convert to WAV
            wav_path = await self.convert_webm_to_wav(file_path)
            
            return wav_path
        finally:
            # Clean up original downloaded file (but keep the WAV file for services to use)
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                    logger.info(f"Cleaned up original downloaded file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up original file {file_path}: {str(e)}")

    @staticmethod
    async def download_audio(url: str) -> str:
        """Download audio file from URL"""
        file_extension = os.path.splitext(url)[1].lower() or '.tmp'
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
        temp_path = temp.name
        temp.close()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download audio: {response.reason}")
                    with open(temp_path, 'wb') as f:
                        f.write(await response.read())
            logger.info(f"Successfully downloaded audio from {url} to {temp_path}")
            return temp_path
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise Exception(f"Failed to download audio: {str(e)}")

    @staticmethod
    async def convert_webm_to_wav(input_file: str) -> str:
        """Convert WebM (or other audio) to WAV format for speech analysis"""
        wav_file = os.path.splitext(input_file)[0] + '.wav'
        command = [
            'ffmpeg',
            '-i', input_file,
            '-acodec', 'pcm_s16le',  # 16-bit PCM
            '-ar', '16000',          # 16kHz sample rate  
            '-ac', '1',              # Mono
            '-y',                    # Overwrite output
            wav_file
        ]
        
        try:
            subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            logger.info(f"Successfully converted {input_file} to {wav_file}")
            return wav_file
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to convert to WAV: {e.stderr.decode()}")
        except Exception as e:
            raise Exception(f"Error converting to WAV: {str(e)}")