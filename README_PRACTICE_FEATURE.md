# Practice Feature Implementation

## Overview

The practice feature allows users to improve their pronunciation by practicing with their improved transcripts. It consists of two parts:

1. **Improved Transcript**: Already available from the main analysis flow under `paragraph_restructuring.improved_transcript`
2. **Pronunciation Practice**: New endpoint for real-time pronunciation analysis

## Architecture

### Option 1: Direct Async Endpoint (Implemented)
- User submits audio URL + transcript → waits 5-8 seconds → gets results
- Simple, reliable, easy to debug
- No pub/sub complexity

## API Endpoints

### Practice Pronunciation Analysis

**Endpoint**: `POST /api/v1/practice/analyze-pronunciation`

**Input**: 
- `audio_url`: Publicly accessible URL to audio file (WAV, MP3, M4A, WebM, OGG)
- `transcript`: Reference transcript text (improved transcript from analysis results)
- `user_id`: Optional user identifier for tracking

**Example Frontend Usage**:
```javascript
// 1. User gets improved transcript from analysis results
const improvedTranscript = analysisResults.section_feedback.paragraph_restructuring.improved_transcript;

// 2. User records new audio and uploads it to get a public URL
const audioUrl = await uploadAudioAndGetUrl(recordedAudioBlob);

// 3. Submit for pronunciation practice
const response = await fetch('/api/v1/practice/analyze-pronunciation', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        audio_url: audioUrl,
        transcript: improvedTranscript,
        user_id: currentUserId // optional
    })
});

const result = await response.json();
```

**Response Format**:
```json
{
    "overall_pronunciation_score": 85.5,
    "accuracy_score": 88.0,
    "fluency_score": 82.0,
    "prosody_score": 87.0,
    "completeness_score": 90.0,
    "word_details": [
        {
            "word": "hello",
            "accuracy_score": 95.0,
            "error_type": "None",
            "duration": 0.5,
            "offset": 0.0
        }
    ],
    "critical_errors": [
        {
            "type": "mispronunciation",
            "word": "world",
            "issue": "vowel_substitution"
        }
    ],
    "improvement_suggestions": "Focus on clearer vowel pronunciation in words like 'world'.",
    "processing_time_ms": 4520,
    "audio_duration_seconds": 3.2,
    "transcript_used": "Hello world, this is my improved practice transcript."
}
```

### Health Check

**Endpoint**: `GET /api/v1/practice/health`

**Response**:
```json
{
    "status": "healthy",
    "service": "practice"
}
```

## User Flow

1. **Complete Analysis**: User submits audio and gets full analysis results
2. **View Improved Transcript**: User sees `paragraph_restructuring.improved_transcript`
3. **Practice Pronunciation**: User clicks "Practice pronunciation" button
4. **Record Audio**: Frontend records user reading the improved transcript
5. **Upload Audio**: Frontend uploads audio and gets publicly accessible URL
6. **Get Feedback**: System analyzes pronunciation and returns detailed feedback
7. **Iterate**: User can practice multiple times with the same improved transcript

## Implementation Details

### File Handling
- Downloads audio from publicly accessible URLs
- Temporary files are automatically cleaned up after processing
- Supports multiple audio formats (converted to WAV internally)
- Uses existing `AudioService` and `PronunciationService`

### Processing Time
- Typically 3-8 seconds depending on audio length
- User sees loading indicator during processing
- Immediate error handling for invalid inputs

### Error Handling
- Validates transcript is not empty
- Validates audio URL format
- Handles audio download/conversion failures gracefully
- Provides meaningful error messages
- Automatic cleanup of temporary files

## Integration with Existing System

### Reused Services
- `PronunciationService.analyze_pronunciation()` - Full pronunciation analysis
- `AudioService.download_audio()` - Download from URL
- `AudioService.convert_webm_to_wav()` - Audio format conversion
- Existing error handling and logging patterns

### Independent from Main Flow
- Completely separate from submission/analysis pub/sub pipeline
- No interference with existing grading system
- Can be used while main system is processing other submissions

## Testing

### Manual Testing
```bash
# Start the server
python -m uvicorn app.main:app --reload

# Test health endpoint
curl http://localhost:8000/api/v1/practice/health

# Test pronunciation analysis (requires publicly accessible audio URL)
curl -X POST http://localhost:8000/api/v1/practice/analyze-pronunciation \
  -H "Content-Type: application/json" \
  -d '{
    "audio_url": "https://example.com/path/to/audio.wav",
    "transcript": "This is a test transcript for pronunciation practice.",
    "user_id": "test_user"
  }'
```

### Frontend Integration
The practice feature can be integrated into your frontend by:
1. Extracting improved transcript from analysis results
2. Recording user audio with Web Audio API
3. Uploading audio to get a publicly accessible URL
4. Submitting audio URL + transcript to practice endpoint
5. Displaying pronunciation feedback in UI

## Future Enhancements

If you want to upgrade to real-time delivery later:
1. Add pub/sub topics for practice pronunciation
2. Implement webhook delivery
3. Add progress indicators during processing
4. Support batch practice sessions

But the current direct endpoint approach works well for most use cases and is much simpler to maintain.

## Files Created

### Core Implementation
- `app/models/practice_model.py` - Pydantic models for requests/responses
- `app/api/v1/endpoints/practice_endpoint.py` - Practice pronunciation endpoint
- `app/api/v1/router.py` - Updated to include practice routes (modified)

### API Structure
```
POST /api/v1/practice/analyze-pronunciation
GET  /api/v1/practice/health
```

### Key Features
- ✅ Audio URL input (no file uploads needed)
- ✅ Reuses existing pronunciation analysis
- ✅ Automatic file cleanup
- ✅ Comprehensive error handling
- ✅ Optional user tracking
- ✅ Direct response (no webhooks) 