from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class TranscriptCleaningRequest(BaseModel):
    """Request model for transcript cleaning"""
    transcript: str = Field(..., description="Original transcript text to clean")
    include_summary: bool = Field(default=False, description="Whether to include cleaning summary statistics")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "transcript": "Um, I think, uh, this is a good, like, example of, you know, how it works.",
                "include_summary": True
            }
        }
    }


class TranscriptCleaningResult(BaseModel):
    """Result model for transcript cleaning"""
    original_transcript: str = Field(..., description="Original transcript text")
    clean_transcript: str = Field(..., description="Cleaned transcript with filler words removed")
    cleaning_summary: Optional[Dict[str, Any]] = Field(default=None, description="Summary of cleaning operations performed")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "original_transcript": "Um, I think, uh, this is a good, like, example of, you know, how it works.",
                "clean_transcript": "I think this is a good example of how it works.",
                "cleaning_summary": {
                    "original_word_count": 14,
                    "cleaned_word_count": 10,
                    "words_removed": 4,
                    "filler_words_removed": ["um", "uh", "like", "you know"],
                    "character_reduction": 25
                }
            }
        }
    }


class BatchTranscriptCleaningRequest(BaseModel):
    """Request model for batch transcript cleaning"""
    transcripts: List[str] = Field(..., description="List of transcript texts to clean")
    include_summary: bool = Field(default=False, description="Whether to include cleaning summaries")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "transcripts": [
                    "Um, hello there, uh, how are you?",
                    "I think, like, this is working well, you know?"
                ],
                "include_summary": True
            }
        }
    }


class BatchTranscriptCleaningResult(BaseModel):
    """Result model for batch transcript cleaning"""
    results: List[TranscriptCleaningResult] = Field(..., description="List of cleaning results")
    batch_summary: Optional[Dict[str, Any]] = Field(default=None, description="Overall batch statistics")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "original_transcript": "Um, hello there, uh, how are you?",
                        "clean_transcript": "Hello there, how are you?",
                        "cleaning_summary": {
                            "words_removed": 2,
                            "filler_words_removed": ["um", "uh"]
                        }
                    }
                ],
                "batch_summary": {
                    "total_transcripts": 2,
                    "total_words_removed": 5,
                    "average_reduction_percent": 25.5
                }
            }
        }
    }


class CleaningSummary(BaseModel):
    """Detailed cleaning summary model"""
    original_word_count: int = Field(..., description="Number of words in original transcript")
    cleaned_word_count: int = Field(..., description="Number of words in cleaned transcript") 
    words_removed: int = Field(..., description="Total number of words removed")
    filler_words_removed: List[str] = Field(default_factory=list, description="List of filler words that were removed")
    character_reduction: int = Field(..., description="Number of characters reduced")
    reduction_percentage: float = Field(..., description="Percentage of text reduced")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "original_word_count": 20,
                "cleaned_word_count": 15,
                "words_removed": 5,
                "filler_words_removed": ["um", "uh", "like", "you know"],
                "character_reduction": 30,
                "reduction_percentage": 25.0
            }
        }
    }