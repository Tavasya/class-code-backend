# Data Structures and Models

## 📊 Overview

The Audio Analysis API uses Pydantic models for type safety, data validation, and clear API contracts. All models are located in the `app/models/` directory.

## 🏗️ Model Categories

### 1. **Request/Response Models** - API endpoints
### 2. **Message Models** - Pub/Sub communication
### 3. **Analysis Result Models** - Service outputs
### 4. **Configuration Models** - System settings

## 📋 Request/Response Models

### Submission Models
**File**: `app/models/submission_model.py` (10 lines)

```python
class SubmissionRequest(BaseModel):
    audio_urls: List[str]
    submission_url: str

class SubmissionResponse(BaseModel):
    message: str
    submission_id: str
    status: str
```

**Usage**: Main entry point for audio submission requests

### Audio Models
**File**: `app/models/audio_model.py` (9 lines)

```python
class AudioConvertRequest(BaseModel):
    audio_url: str
    question_number: int
    submission_url: str

class AudioConvertResponse(BaseModel):
    wav_path: str
    question_number: int
    original_audio_url: str
    status: str
```

**Usage**: Audio conversion and processing operations

### Transcription Models
**File**: `app/models/transcription_model.py` (9 lines)

```python
class TranscriptionRequest(BaseModel):
    audio_url: str
    question_number: int
    submission_url: str

class TranscriptionResponse(BaseModel):
    text: str
    confidence: float
    question_number: int
    processing_time: float
```

**Usage**: Speech-to-text conversion operations

## 📨 Message Models for Pub/Sub

### Analysis Models
**File**: `app/models/analysis_model.py` (33 lines)

```python
class AudioDoneMessage(BaseModel):
    """Message for audio conversion completion"""
    wav_path: str
    question_number: int
    submission_url: str
    original_audio_url: str
    session_id: Optional[str] = None
    total_questions: Optional[int] = None

class TranscriptionDoneMessage(BaseModel):
    """Message for transcription completion"""
    text: str
    error: Optional[str] = None
    question_number: int
    submission_url: str
    audio_url: str
    total_questions: Optional[int] = None

class QuestionAnalysisReadyMessage(BaseModel):
    """Message when question is ready for analysis"""
    wav_path: str
    transcript: str
    question_number: int
    submission_url: str
    audio_url: str
    session_id: Optional[str] = None
    total_questions: Optional[int] = None
```

**Usage**: Coordinate analysis workflow between services

## 🎯 Analysis Result Models

### Pronunciation Models
**File**: `app/models/pronunciation_model.py` (47 lines)

```python
class PhonemeScore(BaseModel):
    phoneme: str
    expected: str
    actual: str
    score: float
    confidence: float

class WordScore(BaseModel):
    word: str
    expected_pronunciation: str
    actual_pronunciation: str
    score: float
    issues: List[str]

class PronunciationAnalysisResult(BaseModel):
    overall_score: float
    phoneme_scores: List[PhonemeScore]
    word_scores: List[WordScore]
    stress_patterns: Dict[str, Any]
    confidence: float
    detailed_feedback: str

class PronunciationRequest(BaseModel):
    wav_path: str
    transcript: str
    question_number: int
    submission_url: str

class PronunciationResponse(BaseModel):
    result: PronunciationAnalysisResult
    processing_time: float
    status: str
```

### Fluency Models
**File**: `app/models/fluency_model.py` (54 lines)

```python
class PauseAnalysis(BaseModel):
    total_pauses: int
    average_pause_duration: float
    pause_ratio: float
    natural_pauses: int
    hesitation_pauses: int

class FillerWords(BaseModel):
    count: int
    types: List[str]
    frequency: float

class FluencyBreak(BaseModel):
    timestamp: float
    type: str
    duration: float

class FluencyAnalysisResult(BaseModel):
    overall_score: float
    words_per_minute: int
    pause_analysis: PauseAnalysis
    filler_words: FillerWords
    rhythm_score: float
    naturalness_score: float
    fluency_breaks: List[FluencyBreak]

class FluencyRequest(BaseModel):
    wav_path: str
    transcript: str
    question_number: int
    submission_url: str

class FluencyResponse(BaseModel):
    result: FluencyAnalysisResult
    processing_time: float
    status: str
```

### Grammar Models
**File**: `app/models/grammar_model.py` (28 lines)

```python
class GrammarError(BaseModel):
    type: str
    original_text: str
    corrected_text: str
    explanation: str
    severity: str
    position: Dict[str, int]

class SentenceStructure(BaseModel):
    score: float
    avg_sentence_length: float
    structure_variety: float
    complex_sentences: int
    compound_sentences: int

class GrammarAnalysisResult(BaseModel):
    overall_score: float
    grammar_errors: List[GrammarError]
    sentence_structure: SentenceStructure
    linguistic_complexity: Dict[str, float]
    suggestions: List[str]

class GrammarRequest(BaseModel):
    transcript: str
    question_number: int
    submission_url: str

class GrammarResponse(BaseModel):
    result: GrammarAnalysisResult
    processing_time: float
    status: str
```

### Lexical Models
**File**: `app/models/lexical_model.py` (19 lines)

```python
class LexicalDiversity(BaseModel):
    type_token_ratio: float
    unique_words: int
    total_words: int
    diversity_score: float

class ComplexityMetrics(BaseModel):
    academic_words: int
    rare_words: int
    complex_words: int
    average_word_length: float

class ReadabilityScores(BaseModel):
    flesch_score: float
    grade_level: str
    complexity_rating: str

class LexicalAnalysisResult(BaseModel):
    overall_score: float
    vocabulary_level: str
    lexical_diversity: LexicalDiversity
    complexity_metrics: ComplexityMetrics
    readability: ReadabilityScores
    word_frequency_analysis: Dict[str, int]

class LexicalRequest(BaseModel):
    transcript: str
    question_number: int
    submission_url: str

class LexicalResponse(BaseModel):
    result: LexicalAnalysisResult
    processing_time: float
    status: str
```

### Vocabulary Models
**File**: `app/models/vocabulary_model.py` (20 lines)

```python
class VocabularyEnhancement(BaseModel):
    original_word: str
    alternatives: List[str]
    context: str
    improvement_level: str

class AcademicVocabulary(BaseModel):
    count: int
    words: List[str]
    percentage: float

class WordChoiceAnalysis(BaseModel):
    word: str
    level: str
    appropriateness: str
    frequency: str

class VocabularyAnalysisResult(BaseModel):
    overall_score: float
    vocabulary_range: str
    enhancement_suggestions: List[VocabularyEnhancement]
    academic_vocabulary: AcademicVocabulary
    word_choice_analysis: List[WordChoiceAnalysis]
    vocabulary_gaps: List[str]

class VocabularyRequest(BaseModel):
    transcript: str
    question_number: int
    submission_url: str

class VocabularyResponse(BaseModel):
    result: VocabularyAnalysisResult
    processing_time: float
    status: str
```

## 🔧 Schema Utilities
**File**: `app/models/schemas.py` (12 lines)

```python
class BaseResponse(BaseModel):
    """Base response model with common fields"""
    status: str
    timestamp: datetime
    processing_time: Optional[float] = None

class ErrorResponse(BaseModel):
    """Standardized error response"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

class HealthCheckResponse(BaseModel):
    """Health check endpoint response"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, str]
```

## 📐 Model Design Patterns

### 1. **Request/Response Pattern**
All endpoints follow consistent request/response structure:
```python
class ServiceRequest(BaseModel):
    # Input parameters
    
class ServiceResponse(BaseModel):
    result: ServiceAnalysisResult
    processing_time: float
    status: str
```

### 2. **Nested Result Models**
Complex analysis results use nested models:
```python
class AnalysisResult(BaseModel):
    overall_score: float
    detailed_metrics: DetailedMetrics
    suggestions: List[str]
```

### 3. **Optional Fields**
Use Optional for fields that may not always be present:
```python
class Message(BaseModel):
    required_field: str
    optional_field: Optional[str] = None
    session_id: Optional[str] = None  # For file lifecycle
```

### 4. **Timestamp Fields**
Consistent timestamp handling:
```python
from datetime import datetime

class TimestampedModel(BaseModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
```

## 🔍 Validation Rules

### URL Validation
```python
from pydantic import HttpUrl

class SubmissionRequest(BaseModel):
    audio_urls: List[HttpUrl]  # Automatically validates URLs
    submission_url: HttpUrl
```

### Score Validation
```python
from pydantic import Field

class ScoreModel(BaseModel):
    score: float = Field(ge=0.0, le=100.0)  # Between 0-100
    confidence: float = Field(ge=0.0, le=1.0)  # Between 0-1
```

### String Constraints
```python
class TextModel(BaseModel):
    transcript: str = Field(min_length=1, max_length=10000)
    word: str = Field(regex=r'^[a-zA-Z]+$')  # Only letters
```

## 📊 Data Flow Through Models

### 1. **API Request Flow**
```
Frontend → SubmissionRequest → SubmissionService → Pub/Sub Messages
```

### 2. **Processing Flow**
```
Pub/Sub → AudioDoneMessage → AnalysisCoordinator → QuestionAnalysisReadyMessage
```

### 3. **Analysis Flow**
```
QuestionAnalysisReadyMessage → AnalysisRequest → AnalysisResult → AnalysisResponse
```

### 4. **Response Flow**
```
AnalysisResponse → DatabaseService → AggregatedResults → WebhookNotification
```

## 🛡️ Type Safety Benefits

### 1. **Compile-time Validation**
- Pydantic validates data types at runtime
- IDE support with type hints
- Automatic serialization/deserialization

### 2. **API Documentation**
- FastAPI automatically generates OpenAPI schemas
- Interactive documentation with examples
- Clear contract definition

### 3. **Error Prevention**
- Prevents type-related runtime errors
- Clear validation error messages
- Consistent data structures across services

## 🔄 Model Evolution

### Versioning Strategy
```python
class SubmissionRequestV1(BaseModel):
    # Original fields
    
class SubmissionRequestV2(SubmissionRequestV1):
    # Additional fields with defaults
    new_field: Optional[str] = None
```

### Backward Compatibility
- Use Optional fields for new additions
- Provide default values for new fields
- Maintain support for older message formats

### Migration Patterns
```python
def migrate_v1_to_v2(v1_data: dict) -> dict:
    """Migrate old format to new format"""
    v2_data = v1_data.copy()
    v2_data['new_field'] = 'default_value'
    return v2_data
```

## 📝 Best Practices

### 1. **Model Organization**
- Group related models in same file
- Use descriptive class names
- Include docstrings for complex models

### 2. **Field Naming**
- Use snake_case for field names
- Be descriptive but concise
- Avoid abbreviations

### 3. **Validation**
- Add appropriate constraints
- Use custom validators for complex logic
- Provide clear error messages

### 4. **Documentation**
- Include field descriptions
- Add examples for complex structures
- Document validation rules 