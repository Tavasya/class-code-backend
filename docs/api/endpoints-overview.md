# API Endpoints Overview

## 📋 Complete Endpoint Listing

The Audio Analysis API provides REST endpoints organized by functionality. All endpoints are prefixed with `/api/v1`.

## 🏥 Health & Monitoring

### Health Check
- **GET** `/api/v1/health/health`
- **Purpose**: System health monitoring
- **File**: `app/api/v1/endpoints/health.py`
- **Response**: System status and basic information

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0"
}
```

## 🎯 Gateway Endpoints

### Audio Submission
- **POST** `/api/v1/submission/submit`
- **Purpose**: Main entry point for audio analysis requests
- **File**: `app/api/v1/endpoints/submission_endpoint.py`
- **Handler**: Accepts both direct requests and Pub/Sub push messages

**Request Schema:**
```json
{
  "audio_urls": [
    "https://example.com/audio1.mp3",
    "https://example.com/audio2.mp3"
  ],
  "submission_url": "https://frontend.com/submission/123"
}
```

**Response Schema:**
```json
{
  "message": "Submission received and processing started",
  "submission_id": "sub_123456",
  "status": "processing"
}
```

## 🎵 Audio Processing

### Audio Conversion
- **POST** `/api/v1/audio/audio_proccessing`
- **Purpose**: Convert audio files to WAV format
- **File**: `app/api/v1/endpoints/audio_endpoint.py`
- **Handler**: Supports both direct API calls and Pub/Sub messages

**Request Schema:**
```json
{
  "audio_url": "https://example.com/audio.mp3",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123"
}
```

**Response Schema:**
```json
{
  "wav_path": "/tmp/session_123/audio_1.wav",
  "question_number": 1,
  "original_audio_url": "https://example.com/audio.mp3",
  "status": "converted"
}
```

### Transcription
- **POST** `/api/v1/transcription/transcribe`
- **Purpose**: Convert audio to text using Azure Speech or AssemblyAI
- **File**: `app/api/v1/endpoints/transcription_endpoint.py`

**Request Schema:**
```json
{
  "audio_url": "https://example.com/audio.mp3",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123"
}
```

**Response Schema:**
```json
{
  "text": "This is the transcribed text from the audio file.",
  "confidence": 0.95,
  "question_number": 1,
  "processing_time": 2.3
}
```

## 🔍 Analysis Services

### Pronunciation Analysis
- **POST** `/api/v1/pronunciation/analyze`
- **Purpose**: Analyze pronunciation accuracy and phonetic correctness
- **File**: `app/api/v1/endpoints/pronunciation_endpoint.py`

**Request Schema:**
```json
{
  "wav_path": "/tmp/audio.wav",
  "transcript": "Hello world",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123"
}
```

**Response Schema:**
```json
{
  "overall_score": 85.5,
  "phoneme_scores": [
    {"phoneme": "h", "score": 90.0},
    {"phoneme": "ɛ", "score": 82.5}
  ],
  "word_scores": [
    {"word": "hello", "score": 88.0},
    {"word": "world", "score": 83.0}
  ],
  "confidence": 0.89,
  "detailed_feedback": "..."
}
```

### Fluency Analysis
- **POST** `/api/v1/fluency/analyze`
- **Purpose**: Assess speaking fluency, pace, and natural flow
- **File**: `app/api/v1/endpoints/fluency_endpoint.py`

**Request Schema:**
```json
{
  "wav_path": "/tmp/audio.wav",
  "transcript": "This is my response to the question.",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123"
}
```

**Response Schema:**
```json
{
  "overall_score": 78.9,
  "words_per_minute": 145,
  "pause_analysis": {
    "total_pauses": 3,
    "average_pause_duration": 0.8,
    "pause_ratio": 0.12
  },
  "filler_words": ["um", "uh"],
  "rhythm_score": 82.0,
  "naturalness_score": 75.0
}
```

### Grammar Analysis
- **POST** `/api/v1/grammar/analyze`
- **Purpose**: Evaluate grammatical correctness and structure
- **File**: `app/api/v1/endpoints/grammar_endpoint.py`

**Request Schema:**
```json
{
  "transcript": "This is the text to analyze for grammar.",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123"
}
```

**Response Schema:**
```json
{
  "overall_score": 84.2,
  "grammar_errors": [
    {
      "type": "subject_verb_agreement",
      "text": "they was going",
      "suggestion": "they were going",
      "severity": "high"
    }
  ],
  "sentence_structure_score": 88.0,
  "complexity_score": 76.0,
  "error_count": 2
}
```

### Lexical Analysis
- **POST** `/api/v1/lexical/analyze`
- **Purpose**: Analyze vocabulary complexity and word choice
- **File**: `app/api/v1/endpoints/lexical_endpoint.py`

**Request Schema:**
```json
{
  "transcript": "The sophisticated methodology demonstrates comprehensive understanding.",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123"
}
```

**Response Schema:**
```json
{
  "overall_score": 80.1,
  "vocabulary_level": "advanced",
  "complexity_metrics": {
    "lexical_diversity": 0.85,
    "academic_words": 3,
    "rare_words": 2
  },
  "readability_score": 78.5,
  "word_frequency_analysis": {...}
}
```

### Vocabulary Analysis
- **POST** `/api/v1/vocabulary/analyze`
- **Purpose**: Assess vocabulary usage and enhancement opportunities
- **File**: `app/api/v1/endpoints/vocabulary_endpoint.py`

**Request Schema:**
```json
{
  "transcript": "I utilized various methodologies to accomplish the task.",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123"
}
```

**Response Schema:**
```json
{
  "overall_score": 83.7,
  "vocabulary_range": "intermediate-advanced",
  "word_choices": [
    {
      "word": "utilized",
      "level": "advanced",
      "alternatives": ["used", "employed"]
    }
  ],
  "enhancement_suggestions": [...],
  "academic_vocabulary_count": 4
}
```

## 🔗 Webhook Endpoints

### Webhook Handler
- **POST** `/api/v1/webhooks/receive`
- **Purpose**: Handle incoming webhook notifications
- **File**: `app/api/v1/endpoints/webhooks_endpoint.py`

### Webhook Delivery
- **POST** `/api/v1/webhooks/deliver`
- **Purpose**: Send webhook notifications to external systems
- **Authentication**: Bearer token or signature verification

## 📊 Results & Testing

### Get Results
- **GET** `/api/v1/results/{submission_id}`
- **Purpose**: Retrieve analysis results for a submission
- **File**: `app/api/v1/endpoints/results_endpoint.py`

**Response Schema:**
```json
{
  "submission_id": "sub_123456",
  "overall_score": 82.3,
  "individual_scores": {
    "pronunciation": 85.5,
    "fluency": 78.9,
    "grammar": 84.2,
    "lexical": 80.1,
    "vocabulary": 83.7
  },
  "detailed_analysis": {...},
  "completed_at": "2024-01-15T10:30:00Z"
}
```

### Debug Endpoints
- **GET** `/api/v1/debug/system-info`
- **GET** `/api/v1/debug/pubsub-status`
- **GET** `/api/v1/debug/service-health`
- **Purpose**: Development and debugging utilities
- **File**: `app/api/v1/endpoints/debug_endpoint.py`

## 🔒 Authentication & Security

### CORS Configuration
```python
CORS_ORIGINS = [
    "https://class-code-nu.vercel.app",
    "https://www.class-code-nu.vercel.app",
    "http://localhost:8080",
    "http://localhost:8081",
    "https://app.nativespeaking.ai",
    "http://localhost:5173",
    "https://native-devserver.vercel.app"
]
```

### Request Validation
- All requests validated using Pydantic models
- Type checking and data validation enforced
- Error responses include detailed validation messages

### Error Handling
- Standardized error response format
- HTTP status codes follow REST conventions
- Detailed error logging for debugging

## 📝 Request/Response Patterns

### Standard Error Response
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request data",
    "details": [
      {
        "field": "audio_url",
        "message": "Invalid URL format"
      }
    ]
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Pub/Sub Message Format
Many endpoints support both direct HTTP requests and Pub/Sub push messages:

```json
{
  "message": {
    "data": "base64_encoded_json_payload",
    "attributes": {},
    "messageId": "msg_123456"
  }
}
```

## 🚀 Performance Considerations

### Asynchronous Processing
- Long-running analysis tasks handled asynchronously
- Immediate response with status tracking
- Webhook notifications for completion

### Rate Limiting
- Built-in FastAPI rate limiting
- Per-endpoint throttling capabilities
- Graceful handling of rate limit exceeded

### Caching
- Results caching for duplicate submissions
- Audio file caching during processing
- Configurable cache expiration times

## 📊 Monitoring & Metrics

### Built-in Metrics
- Request/response times
- Success/error rates
- Service health status
- Resource utilization

### Custom Metrics
- Analysis accuracy scores
- Processing pipeline performance
- External API response times
- File processing statistics 