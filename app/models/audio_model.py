from pydantic import BaseModel

class AudioConvertRequest(BaseModel):
    url: str
    question_number: int = 1

class AudioConvertResponse(BaseModel):
    wav_path: str
    question_number: int = 1