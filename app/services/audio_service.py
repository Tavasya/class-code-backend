import os
import aiohttp
import tempfile
import subprocess
import logging
import uuid
from app.services.file_manager_service import file_manager
from app.services.http_client import get_shared_session
from app.core.config import supabase

logger = logging.getLogger(__name__)

# Bucket name for converted audio files
CONVERTED_AUDIO_BUCKET = "converted-audio"

class AudioService:
    def __init__(self):
        pass

    async def process_single_audio(self, audio_url: str, question_number: int, submission_url: str) -> dict:
        """Process a single audio URL with centralized file management

        Now uploads WAV to Supabase Storage to ensure availability across Cloud Run instances.
        """
        try:
            # Generate session ID for this file
            session_id = file_manager.generate_session_id(submission_url, question_number)

            # Download and convert audio to WAV
            local_wav_path = await self.convert_to_wav(audio_url)

            try:
                # Upload WAV to Supabase Storage for cross-instance access
                storage_url = await self.upload_wav_to_storage(
                    local_wav_path,
                    submission_url,
                    question_number
                )
                logger.info(f"Uploaded WAV to Supabase Storage: {storage_url}")

                # Store metadata for potential retries
                metadata = {
                    "original_audio_url": audio_url,
                    "question_number": question_number,
                    "submission_url": submission_url,
                    "storage_url": storage_url
                }

                # Register for cleanup tracking (optional now since file is in cloud storage)
                await file_manager.register_file_session(
                    session_id=session_id,
                    file_path=local_wav_path,
                    dependent_services={"pronunciation"},
                    cleanup_timeout_minutes=30,
                    metadata=metadata
                )

                return {
                    "wav_path": storage_url,  # Return storage URL instead of local path
                    "local_wav_path": local_wav_path,  # Keep local path for backwards compatibility
                    "session_id": session_id,
                    "question_number": question_number
                }
            finally:
                # Clean up local WAV file after upload to storage
                if local_wav_path and os.path.exists(local_wav_path):
                    try:
                        os.unlink(local_wav_path)
                        logger.info(f"Cleaned up local WAV file after upload: {local_wav_path}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up local WAV file {local_wav_path}: {str(e)}")

        except Exception as e:
            logger.error(f"Error processing audio URL {audio_url} for question {question_number}: {str(e)}")
            raise

    async def upload_wav_to_storage(self, local_wav_path: str, submission_url: str, question_number: int) -> str:
        """Upload WAV file to Supabase Storage and return public URL"""
        if not supabase:
            raise Exception("Supabase client not initialized")

        try:
            # Generate unique filename
            unique_id = str(uuid.uuid4())[:8]
            storage_path = f"wav/{submission_url}/{question_number}_{unique_id}.wav"

            # Read file content
            with open(local_wav_path, 'rb') as f:
                file_content = f.read()

            # Upload to Supabase Storage
            response = supabase.storage.from_(CONVERTED_AUDIO_BUCKET).upload(
                path=storage_path,
                file=file_content,
                file_options={"content-type": "audio/wav"}
            )

            # Get public URL
            public_url = supabase.storage.from_(CONVERTED_AUDIO_BUCKET).get_public_url(storage_path)

            logger.info(f"Successfully uploaded WAV to storage: {storage_path}")
            return public_url

        except Exception as e:
            logger.error(f"Failed to upload WAV to Supabase Storage: {str(e)}")
            raise Exception(f"Failed to upload WAV to storage: {str(e)}")

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
            session = await get_shared_session()
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