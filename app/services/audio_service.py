import os
import aiohttp
import tempfile
import subprocess

class AudioService:
    async def convert_to_wav(self, audio_url: str) -> str:
        """Download audio from Supabase and convert to WAV for speech analysis"""
        # Download from Supabase
        file_path = await self.download_audio(audio_url)
        
        # Convert to WAV
        wav_path = await self.convert_webm_to_wav(file_path)
        
        # Clean up original file
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            
        return wav_path

    @staticmethod
    async def download_audio(url: str) -> str:
        """Download audio file from Supabase URL"""
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
            return wav_file
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to convert to WAV: {e.stderr.decode()}")
        except Exception as e:
            raise Exception(f"Error converting to WAV: {str(e)}")