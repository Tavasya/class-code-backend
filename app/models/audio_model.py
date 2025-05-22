from pydantic import BaseModel

class AudioConvertRequest(BaseModel):
    url: str

class AudioConvertResponse(BaseModel):
    wav_path: str