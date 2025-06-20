# Data Flow Architecture

## 📊 Overview

This document describes how data flows through the Audio Analysis API system, from initial submission to final results delivery.

## 🔄 Complete Data Flow Diagram

```
Frontend
    ↓ POST /api/v1/submission/submit
    ↓ {audio_urls: [...], submission_url: "..."}
    ↓
SubmissionService
    ↓ Validates submission
    ↓ Publishes to STUDENT_SUBMISSION topic
    ↓
PubSub → STUDENT_SUBMISSION → AudioService
    ↓ Downloads & converts audio to WAV
    ↓ Publishes to AUDIO_CONVERSION_DONE topic
    ↓
PubSub → AUDIO_CONVERSION_DONE → AnalysisCoordinator
    ↓ Tracks audio completion state
    ↓
    ↓ (Parallel Process)
    ↓
PubSub → STUDENT_SUBMISSION → TranscriptionService  
    ↓ Converts audio to text (Azure/AssemblyAI)
    ↓ Publishes to TRANSCRIPTION_DONE topic
    ↓
PubSub → TRANSCRIPTION_DONE → AnalysisCoordinator
    ↓ Tracks transcription completion state
    ↓ When both audio & transcript ready
    ↓ Publishes to QUESTION_ANALYSIS_READY topic
    ↓
PubSub → QUESTION_ANALYSIS_READY → Analysis Services (Parallel)
    ├─ PronunciationService → PRONUNCIATION_DONE
    ├─ FluencyService → FLUENCY_DONE  
    ├─ GrammarService → GRAMMER_DONE
    ├─ LexicalService → LEXICAL_DONE
    └─ VocabularyService → VOCABULARY_DONE
    ↓
PubSub → Analysis Done Topics → DatabaseService
    ↓ Stores individual analysis results
    ↓ Aggregates results when all complete
    ↓ Publishes to SUBMISSION_ANALYSIS_COMPLETE
    ↓
PubSub → SUBMISSION_ANALYSIS_COMPLETE → WebhookService
    ↓ Notifies frontend via webhook
    ↓
Frontend receives completion notification
```

## 📋 Step-by-Step Data Flow

### 1. **Initial Submission** 
**File**: `app/api/v1/endpoints/submission_endpoint.py`

```json
Input: {
  "audio_urls": ["https://example.com/audio1.mp3", "..."],
  "submission_url": "https://frontend.com/submission/123"
}
```

**Process:**
- Validates request structure
- Creates `SubmissionRequest` model
- Passes to `SubmissionService`

### 2. **Submission Processing**
**File**: `app/services/submission_service.py`

**Process:**
- Validates audio URLs accessibility
- Publishes individual messages to `STUDENT_SUBMISSION` topic
- Each audio gets separate processing pipeline
- Returns immediate acknowledgment to frontend

### 3. **Audio Processing Branch**
**File**: `app/services/audio_service.py`

**Input from Pub/Sub:**
```json
{
  "audio_url": "https://example.com/audio.mp3",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123"
}
```

**Process:**
- Downloads audio file
- Converts to WAV format using FFmpeg
- Stores temporarily with session management
- Publishes `AudioDoneMessage` to `AUDIO_CONVERSION_DONE`

**Output:**
```json
{
  "wav_path": "/tmp/session_123/audio_1.wav",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123",
  "original_audio_url": "https://example.com/audio.mp3",
  "session_id": "session_123"
}
```

### 4. **Transcription Processing Branch**
**File**: `app/services/transcription_service.py`

**Process:**
- Uses Azure Speech Services or AssemblyAI
- Converts audio URL directly to text
- Handles multiple audio formats
- Publishes `TranscriptionDoneMessage` to `TRANSCRIPTION_DONE`

**Output:**
```json
{
  "text": "Hello, this is my audio submission...",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123",
  "audio_url": "https://example.com/audio.mp3"
}
```

### 5. **Analysis Coordination**
**File**: `app/services/analysis_coordinator_service.py`

**State Management:**
- Tracks completion of both audio conversion and transcription
- Uses in-memory state dictionary keyed by `submission_url:question_number`
- When both processes complete, publishes to `QUESTION_ANALYSIS_READY`

**Coordination Logic:**
```python
state = {
    "audio_done": True/False,
    "transcript_done": True/False,
    "audio_data": AudioDoneMessage,
    "transcript_data": TranscriptionDoneMessage
}
```

### 6. **Parallel Analysis Services**

#### A. **Pronunciation Analysis**
**File**: `app/services/pronunciation_service.py`

**Process:**
- Analyzes WAV file using phonetic analysis
- Compares with expected pronunciation patterns
- Uses CMU Dictionary and spaCy
- Scores individual phonemes and overall accuracy

**Output:**
```json
{
  "overall_score": 85.5,
  "phoneme_scores": [...],
  "word_scores": [...],
  "confidence": 0.89
}
```

#### B. **Fluency Analysis**
**File**: `app/services/fluency_service.py`

**Process:**
- Analyzes speech rate, pauses, hesitations
- Calculates words per minute
- Identifies filler words and repetitions
- Uses both audio and transcript data

#### C. **Grammar Analysis**
**File**: `app/services/grammar_service.py`

**Process:**
- Uses OpenAI API for grammar checking
- Analyzes sentence structure
- Identifies grammatical errors
- Provides correction suggestions

#### D. **Lexical Analysis**
**File**: `app/services/lexical_service.py`

**Process:**
- Analyzes vocabulary complexity
- Calculates readability scores
- Identifies academic/advanced vocabulary usage
- Uses spaCy for linguistic analysis

#### E. **Vocabulary Analysis**
**File**: `app/services/vocabulary_service.py`

**Process:**
- Analyzes word choice and variety
- Compares against vocabulary levels
- Uses external vocabulary datasets
- Provides vocabulary enhancement suggestions

### 7. **Result Aggregation**
**File**: `app/services/database_service.py`

**Process:**
- Stores individual analysis results in Supabase
- Tracks completion of all analysis services
- Aggregates final score when all analyses complete
- Calculates weighted overall score

**Final Result Structure:**
```json
{
  "submission_url": "https://frontend.com/submission/123",
  "overall_score": 82.3,
  "pronunciation": {
    "score": 85.5,
    "details": {...}
  },
  "fluency": {
    "score": 78.9,
    "details": {...}
  },
  "grammar": {
    "score": 84.2,
    "details": {...}
  },
  "lexical": {
    "score": 80.1,
    "details": {...}
  },
  "vocabulary": {
    "score": 83.7,
    "details": {...}
  },
  "completed_at": "2024-01-15T10:30:00Z"
}
```

### 8. **Webhook Notification**
**File**: `app/api/v1/endpoints/webhooks_endpoint.py`

**Process:**
- Receives `SUBMISSION_ANALYSIS_COMPLETE` message
- Makes HTTP POST to frontend webhook URL
- Includes complete analysis results
- Handles retry logic for failed webhooks

## 🔄 Message Types and Topics

### Pub/Sub Topics Used:
1. **STUDENT_SUBMISSION** - Initial audio submission
2. **AUDIO_CONVERSION_DONE** - Audio processing complete
3. **TRANSCRIPTION_DONE** - Speech-to-text complete
4. **QUESTION_ANALYSIS_READY** - Ready for analysis services
5. **PRONUNCIATION_DONE** - Pronunciation analysis complete
6. **FLUENCY_DONE** - Fluency analysis complete
7. **GRAMMER_DONE** - Grammar analysis complete
8. **LEXICAL_DONE** - Lexical analysis complete
9. **VOCABULARY_DONE** - Vocabulary analysis complete
10. **SUBMISSION_ANALYSIS_COMPLETE** - All analysis complete

## ⚡ Asynchronous Processing Benefits

1. **Scalability**: Each service can scale independently
2. **Reliability**: Message persistence ensures no data loss
3. **Flexibility**: Easy to add new analysis services
4. **Performance**: Parallel processing reduces total time
5. **Monitoring**: Each step can be monitored separately

## 🗄️ Data Storage

### Temporary Data:
- Audio files (cleaned up after processing)
- Session-based file management
- In-memory coordination state

### Persistent Data:
- Analysis results in Supabase
- Submission metadata
- User progress tracking

## 🔍 Error Handling

Each step includes comprehensive error handling:
- Pub/Sub message acknowledgment
- Retry logic for external API calls
- Graceful degradation for failed services
- Detailed logging for debugging 