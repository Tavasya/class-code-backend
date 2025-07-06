# Practice System Design Document

## System Overview

The practice system is designed to provide a complete pronunciation improvement workflow for language learners. The system follows a linear progression from initial recording to targeted pronunciation practice.

### Core Workflow
1. **Initial Recording** - Student records themselves speaking
2. **Transcript Improvement** - AI processes and improves the transcript
3. **Sentence Practice** - Student practices improved sentences one by one
4. **Word Practice** - Student practices individual problematic words
5. **Completion** - Practice session is marked complete

### Architecture Principles
- **Session-based**: Each practice flow is contained within a single session
- **Progressive**: Students move through stages in order
- **Adaptive**: Focus on problematic words identified through analysis
- **Real-time**: Webhook-based pronunciation analysis during practice phases

## Database Design

### Core Tables

Following industry-standard state machine patterns, the practice system uses a single business entity with state transitions:

#### practice_sessions
Handles the entire practice workflow: Recording → Transcription → AI Improvement → Sentence Practice → Word Practice → Completion

**Columns:**
- `id` (UUID, Primary Key) - Unique practice session identifier
- `user_id` (UUID) - User identifier (references users.id)
- `original_audio_url` (TEXT) - URL to initial recording
- `original_transcript` (TEXT) - Raw transcript from speech-to-text
- `improved_transcript` (TEXT) - AI-improved version of the transcript
- `sentences` (JSONB) - Array of sentences extracted from improved transcript
- `current_sentence_index` (INTEGER) - Which sentence they're currently practicing
- `current_word_index` (INTEGER) - Which word within current sentence they're practicing
- `problematic_words` (JSONB) - Words identified as needing practice
- `status` (ENUM) - Current state of the entire practice workflow
- `webhook_session_id` (TEXT) - Active webhook session identifier (null during transcript processing)
- `error_message` (TEXT) - Error details if processing fails
- `created_at` (TIMESTAMP) - Session creation time
- `updated_at` (TIMESTAMP) - Last update time
- `completed_at` (TIMESTAMP) - Session completion time (nullable)

**Status Enum Values (Complete Workflow):**
- `transcript_processing` - Converting audio to text and improving with AI
- `transcript_ready` - Improved transcript is ready, practice can begin
- `practicing_sentences` - Currently practicing sentences
- `practicing_words` - Currently practicing individual words
- `practicing_full_transcript` - Final test: recording entire improved transcript
- `completed` - All practice finished successfully
- `failed` - Processing failed at some stage
- `abandoned` - Session was abandoned by user

#### practice_attempts
Tracks individual pronunciation attempts for sentences and words during the practice phase.

**Columns:**
- `id` (UUID, Primary Key) - Unique attempt identifier
- `session_id` (UUID, Foreign Key) - Reference to practice_sessions
- `attempt_type` (ENUM) - Type of practice attempt
- `content` (TEXT) - The sentence or word being practiced
- `audio_url` (TEXT) - URL to the pronunciation attempt recording
- `pronunciation_score` (DECIMAL) - Overall pronunciation score (0-100)
- `pronunciation_analysis` (JSONB) - Detailed analysis results
- `is_passed` (BOOLEAN) - Whether this attempt passed the threshold
- `attempt_number` (INTEGER) - Which attempt this is for this content
- `created_at` (TIMESTAMP) - When the attempt was made
- `analyzed_at` (TIMESTAMP) - When analysis was completed

**Attempt Type Enum Values:**
- `sentence` - Full sentence practice
- `word` - Individual word practice
- `full_transcript` - Complete improved transcript recording

### Data Relationships

```
practice_sessions (1) -> (many) practice_attempts
├── Single session progresses through entire workflow
├── Phase 1: Audio → Transcript → AI Improvement (status: transcript_processing → transcript_ready)
├── Phase 2: Sentence Practice → Word Practice → Completion (status: practicing_sentences → practicing_words → completed)
├── Current progress tracked via current_sentence_index and current_word_index
└── Attempts are created only during practice phases
```

### Sample Data Structure

**practice_sessions.sentences JSON:**
```json
[
  {
    "index": 0,
    "text": "I believe the most popular mode of transportation is the motorbike.",
    "words": ["I", "believe", "the", "most", "popular", "mode", "of", "transportation", "is", "the", "motorbike"],
    "completed": false,
    "passed": false
  }
]
```

**practice_sessions.problematic_words JSON:**
```json
[
  {
    "word": "transportation",
    "sentence_index": 0,
    "word_index": 7,
    "difficulty_score": 85,
    "completed": false,
    "passed": false
  }
]
```

## API Design

### Core Endpoints

#### 1. Start Practice Session
`POST /api/v1/practice/sessions`

**Request Body:**
```json
{
  "audio_url": "https://example.com/recording.webm",
  "transcript": "optional existing transcript"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "status": "transcript_processing",
  "message": "Processing your audio recording and improving transcript..."
}
```

#### 2. Get Session Status
`GET /api/v1/practice/sessions/{session_id}`

**Response (Transcript Processing):**
```json
{
  "session_id": "uuid",
  "status": "transcript_processing",
  "message": "Still processing your audio..."
}
```

**Response (Ready for Practice):**
```json
{
  "session_id": "uuid",
  "status": "transcript_ready",
  "original_transcript": "Um, I think the most popular...",
  "improved_transcript": "I believe the most popular...",
  "sentences": [{"index": 0, "text": "I believe the most popular mode of transportation is the motorbike."}],
  "ready_for_practice": true
}
```

#### 3. Start Sentence Practice
`POST /api/v1/practice/sessions/{session_id}/start-practice`

**Response:**
```json
{
  "session_id": "uuid",
  "status": "practicing_sentences",
  "webhook_session_started": true,
  "current_sentence": {
    "index": 0,
    "text": "I believe the most popular mode of transportation is the motorbike."
  }
}
```

#### 4. Submit Sentence Practice
`POST /api/v1/practice/sessions/{session_id}/sentences`

**Request Body:**
```json
{
  "sentence_index": 0,
  "audio_url": "https://example.com/sentence-attempt.webm"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "sentence_index": 0,
  "pronunciation_score": 75,
  "passed": false,
  "status": "practicing_words",
  "problematic_words": ["transportation", "motorbike"],
  "analysis": {
    "word_scores": {...},
    "overall_feedback": "..."
  }
}
```

#### 5. Submit Word Practice
`POST /api/v1/practice/sessions/{session_id}/words`

**Request Body:**
```json
{
  "word": "transportation",
  "audio_url": "https://example.com/word-attempt.webm"
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "word": "transportation",
  "pronunciation_score": 85,
  "passed": true,
  "remaining_words": ["motorbike"],
  "analysis": {
    "phoneme_accuracy": {...},
    "feedback": "..."
  }
}
```

#### 6. Get Session Progress
`GET /api/v1/practice/sessions/{session_id}/progress`

**Response:**
```json
{
  "session_id": "uuid",
  "status": "practicing_words",
  "progress": {
    "current_sentence": 0,
    "total_sentences": 3,
    "current_word": 1,
    "total_words_in_sentence": 11,
    "problematic_words_remaining": 1
  },
  "current_content": "motorbike"
}
```

#### 7. Submit Full Transcript Practice
`POST /api/v1/practice/sessions/{session_id}/full-transcript`

**Request Body:**
```json
{
  "audio_url": "https://example.com/full-transcript-attempt.webm"
}
```

**Response (Passed):**
```json
{
  "session_id": "uuid",
  "pronunciation_score": 72,
  "passed": true,
  "status": "completed",
  "analysis": {
    "overall_fluency": 75,
    "overall_feedback": "Great improvement! Well done."
  }
}
```

**Response (Failed):**
```json
{
  "session_id": "uuid", 
  "pronunciation_score": 65,
  "passed": false,
  "status": "practicing_full_transcript",
  "analysis": {
    "overall_fluency": 60,
    "overall_feedback": "Try to speak more slowly and clearly. Focus on the pronunciation improvements you practiced."
  }
}
```

### Frontend Logic

**Realtime-Driven UI Updates:**
The frontend uses Supabase Realtime to receive instant status updates, following existing patterns from `useRealtimeSubmission` and other realtime hooks.

**Status-Based UI Rendering:**
```javascript
// Realtime updates trigger automatic UI changes
const renderPracticeUI = (session) => {
  switch(session.status) {
    case 'transcript_processing':
      return <ProcessingUI message="Improving your transcript..." />;
    
    case 'transcript_ready':
      return <StartPracticeUI 
        improvedTranscript={session.improved_transcript}
        sentences={session.sentences} 
      />;
    
    case 'practicing_sentences':
      return <SentenceRecordingUI 
        currentSentence={session.sentences[session.current_sentence_index]}
        progress={`${session.current_sentence_index + 1}/${session.sentences.length}`}
      />;
    
    case 'practicing_words':
      return <WordRecordingUI 
        problematicWords={session.problematic_words}
        currentWord={session.problematic_words[session.current_word_index]}
      />;
    
    case 'practicing_full_transcript':
      return <FullTranscriptRecordingUI 
        transcript={session.improved_transcript}
        attempt={session.full_transcript_attempts || 1}
      />;
    
    case 'completed':
      return <CompletionUI results={session} />;
  }
};
```

**Realtime Session Data:**
```javascript
// Session data updates automatically via Supabase Realtime
const sessionData = {
  id: "uuid",
  status: "practicing_words",
  current_sentence_index: 0,
  current_word_index: 1,
  problematic_words: ["transportation", "motorbike"],
  sentences: [
    {
      index: 0,
      text: "I believe the most popular mode of transportation is the motorbike.",
      completed: false,
      passed: false
    }
  ],
  improved_transcript: "I believe the most popular...",
  // ... other fields updated in real-time
};
```

**No Manual Status Polling:**
- Frontend automatically receives updates when backend changes database
- UI re-renders instantly on status changes
- Consistent with existing realtime submission tracking
- No `next_action` fields needed - status and progress data drive UI state

## Workflow State Management

### State Transitions

**Phase 1: Transcript Processing**
```
recording_uploaded → transcribing → improving_transcript → transcript_ready
                                ↘ failed (if error occurs)
```

**Phase 2: Pronunciation Practice**
```
ready_to_start → practicing_sentences → practicing_words (if words failed)
practicing_sentences → practicing_sentences (next sentence)
practicing_words → practicing_words (next word)
practicing_words → practicing_sentences (all words passed, retry sentence)
practicing_sentences → practicing_full_transcript (all sentences passed)
practicing_full_transcript → practicing_full_transcript (failed, retry)
practicing_full_transcript → completed (passed final test)
```

**Phase Transition**
```
Phase 1 (transcript_ready) → Phase 2 (ready_to_start)
```

### Business Logic Rules

**Phase 1: Transcript Processing:**
- Create transcript session with `recording_uploaded` status
- If transcript provided, skip transcription, go directly to `improving_transcript`
- If audio_url provided, set status to `transcribing` and process through transcription service
- Once transcript available, set status to `improving_transcript` and enhance with AI
- When complete, set status to `transcript_ready`

**Phase 2: Pronunciation Practice Setup:**
- Create pronunciation session linked to transcript session
- Extract sentences from improved transcript
- Set status to `ready_to_start`
- Start webhook session for real-time analysis
- Set `current_sentence_index` to 0

**Sentence Practice:**
- Set status to `practicing_sentences`
- Student records themselves saying current sentence
- Webhook processes pronunciation analysis
- If score >= 80 (configurable threshold):
  - Mark sentence as passed
  - Move to next sentence or complete
- If score < 80:
  - Identify problematic words
  - Transition to `practicing_words`
  - Set `current_word_index` to 0

**Word Practice:**
- Set status to `practicing_words`
- Student practices each problematic word individually
- Webhook processes word-level pronunciation analysis
- If word score >= 85 (configurable threshold):
  - Mark word as passed
  - Move to next problematic word
- If word score < 85:
  - Increment attempt counter
  - Student retries same word
- When all words passed:
  - Return to sentence practice (`practicing_sentences`)
  - Student re-attempts the full sentence

**Final Transcript Practice:**
- After all sentences pass individually, move to `practicing_full_transcript`
- Student records entire improved transcript in one attempt
- Lower threshold (70-75% vs 80% for sentences) since it's the complete text
- If passed: Session becomes `completed`
- If failed: Student retries full transcript (no sentence breakdown)
- Maximum attempts: 5 for full transcript before offering completion

**Completion:**
- Final transcript recording passed OR maximum attempts reached
- Pronunciation session status becomes `completed`
- `completed_at` timestamp is set
- Webhook session is ended
- Final results are compiled

## Webhook Integration Points

### Webhook Session Lifecycle

**When to Start Webhook Session:**
- NOT during transcript processing (Phase 1)
- START when pronunciation session is created (`ready_to_start` status)
- MAINTAIN throughout sentence and word practice phases (Phase 2)
- END when pronunciation session is completed or abandoned

**Webhook Session Management:**
- Webhook session ID is stored in `practice_sessions.webhook_session_id`
- Session remains active for the entire pronunciation practice phase
- Provides real-time feedback for both sentence and word analysis

**Webhook Triggers:**
1. **Sentence Analysis**: Triggered when student submits sentence recording
2. **Word Analysis**: Triggered when student submits word recording

### Webhook Payload Structure

**For Sentence Analysis:**
```json
{
  "session_id": "uuid",
  "analysis_type": "sentence",
  "audio_url": "https://example.com/recording.webm",
  "expected_text": "I believe the most popular mode of transportation is the motorbike",
  "sentence_index": 0,
  "callback_url": "/api/v1/practice/sessions/{session_id}/webhook/sentence"
}
```

**For Word Analysis:**
```json
{
  "session_id": "uuid",
  "analysis_type": "word",
  "audio_url": "https://example.com/recording.webm",
  "expected_text": "transportation",
  "word_context": "I believe the most popular mode of transportation is the motorbike",
  "callback_url": "/api/v1/practice/sessions/{session_id}/webhook/word"
}
```

## Service Integration

### Existing Services Used

**Phase 1 Services:**
- **TranscriptionService**: Converts audio to text
- **ParagraphRestructuringService**: AI improvement of transcripts

**Phase 2 Services:**
- **PronunciationService**: Sentence and word-level pronunciation analysis
- **Existing Webhook System**: Real-time analysis processing

### New Services Required

**PracticeTranscriptSessionService:**
- Manages Phase 1 transcript processing workflow
- Orchestrates transcription → improvement pipeline
- Handles Phase 1 status transitions

**PracticeSessionService:**
- Manages the complete practice workflow
- Orchestrates sentence → word → completion flow
- Handles status transitions
- Manages webhook session lifecycle

**PracticePronunciationService:**
- Extends existing PronunciationService for practice-specific analysis
- Returns simplified, fast responses optimized for practice workflow
- Handles different attempt types (sentence, word, full_transcript)
- Provides practice-appropriate pass/fail thresholds and phoneme error extraction

**SentenceExtractionService:**
- Parses improved transcript into practice sentences
- Identifies natural sentence boundaries
- Handles complex sentence structures

**WordDifficultyService:**
- Analyzes pronunciation results to identify problematic words
- Prioritizes words for practice based on error patterns
- Maintains difficulty scoring algorithms

## Practice Pronunciation Service Design

### Fast, Practice-Optimized Analysis

The practice system requires **faster, simpler pronunciation analysis** compared to the comprehensive assignment analysis. A dedicated service ensures optimal performance and clean separation.

### Implementation Approach

**Create Practice-Specific Service:**
```python
# New file: app/services/practice_pronunciation_service.py
from app.services.pronunciation_service import PronunciationService

class PracticePronunciationService(PronunciationService):
    """
    Extends existing PronunciationService for practice-specific analysis.
    Optimized for speed with simplified responses.
    """
    
    async def analyze_for_practice(self, audio_url: str, expected_text: str, attempt_type: str):
        """
        Fast pronunciation analysis for practice sessions.
        
        Args:
            audio_url: URL to recorded audio
            expected_text: Text they should have said (sentence/word/full_transcript)
            attempt_type: "sentence", "word", or "full_transcript"
        
        Returns:
            Simplified practice response optimized for speed
        """
        # Reuse existing Azure Speech API call from parent class
        full_analysis = await super().analyze_pronunciation(audio_url, expected_text)
        
        # Transform to practice-optimized response
        return self._transform_for_practice(full_analysis, expected_text, attempt_type)
    
    def _transform_for_practice(self, full_analysis, expected_text, attempt_type):
        """Transform full analysis to practice-specific format"""
        return {
            "content": expected_text,
            "attempt_type": attempt_type,
            "passed": self._determine_practice_pass_fail(full_analysis, attempt_type),
            "pronunciation_score": full_analysis.get("overall_score", 0),
            "phoneme_errors": self._extract_phoneme_errors_for_practice(full_analysis),
            "processing_time_ms": full_analysis.get("processing_time_ms", 0)
        }
    
    def _determine_practice_pass_fail(self, analysis, attempt_type):
        """Practice-specific pass/fail logic with different thresholds"""
        score = analysis.get("overall_score", 0)
        
        thresholds = {
            "sentence": 80,           # 80% for sentences
            "word": 85,              # 85% for individual words  
            "full_transcript": 72    # 72% for full transcript (lower threshold)
        }
        
        return score >= thresholds.get(attempt_type, 80)
    
    def _extract_phoneme_errors_for_practice(self, analysis):
        """Extract only relevant phoneme errors for practice feedback"""
        errors = []
        
        # Extract word-level phoneme errors from Azure response
        for word_result in analysis.get("word_results", []):
            if word_result.get("accuracy_score", 100) < 70:  # Focus on problematic words
                errors.append({
                    "word": word_result.get("word"),
                    "expected_phonemes": word_result.get("phonemes", []),
                    "issues": self._identify_phoneme_issues(word_result),
                    "accuracy": word_result.get("accuracy_score", 0)
                })
        
        return errors[:5]  # Limit to top 5 errors for speed
    
    def _identify_phoneme_issues(self, word_result):
        """Identify specific phoneme pronunciation issues"""
        issues = []
        
        for phoneme in word_result.get("phonemes", []):
            if phoneme.get("accuracy_score", 100) < 60:  # Problematic phonemes
                issues.append({
                    "phoneme": phoneme.get("phoneme"),
                    "accuracy": phoneme.get("accuracy_score"),
                    "issue_type": self._classify_phoneme_issue(phoneme)
                })
        
        return issues[:3]  # Top 3 phoneme issues per word
    
    def _classify_phoneme_issue(self, phoneme):
        """Classify the type of phoneme pronunciation issue"""
        accuracy = phoneme.get("accuracy_score", 100)
        
        if accuracy < 30:
            return "severely_mispronounced"
        elif accuracy < 60:
            return "mispronounced" 
        else:
            return "needs_improvement"
```

### Performance Optimizations

**Speed-Focused Design:**
- **Reuses existing Azure calls** - no additional API latency
- **Simplified response format** - only essential data for practice
- **Limited error details** - top 5 word errors, top 3 phoneme issues per word
- **Fast pass/fail logic** - simple threshold checks
- **Minimal processing** - focused on speed over comprehensive analysis

**Response Size Optimization:**
```json
{
  "content": "transportation",
  "attempt_type": "word",
  "passed": false,
  "pronunciation_score": 65,
  "phoneme_errors": [
    {
      "word": "transportation", 
      "accuracy": 65,
      "issues": [
        {"phoneme": "tr", "accuracy": 45, "issue_type": "mispronounced"},
        {"phoneme": "æ", "accuracy": 55, "issue_type": "needs_improvement"}
      ]
    }
  ],
  "processing_time_ms": 1250
}
```

### Integration with Practice Workflow

**Webhook Usage:**
- Practice sessions use dedicated `PracticePronunciationService`
- Assignment analysis continues using existing `PronunciationService`
- No impact on existing analysis workflow
- Faster processing for practice-specific needs

**Service Selection:**
```python
# In practice webhook handler
if context == "practice":
    service = PracticePronunciationService()
    result = await service.analyze_for_practice(audio_url, expected_text, attempt_type)
else:
    service = PronunciationService()  # Existing assignment analysis
    result = await service.analyze_pronunciation(audio_url, expected_text)
```

## Technical Specifications

### Pronunciation Analysis Thresholds

**Sentence-Level Thresholds:**
- Pass threshold: 80% overall pronunciation score
- Considers: accuracy, fluency, prosody, completeness
- Failing words: Any word with accuracy < 70%

**Word-Level Thresholds:**
- Pass threshold: 85% word pronunciation score
- Considers: phoneme accuracy, stress patterns
- Maximum attempts: 5 per word before suggesting skip

**Full Transcript Thresholds:**
- Pass threshold: 70-75% overall pronunciation score (lower than sentences)
- Considers: overall fluency, pacing, and pronunciation consistency
- Maximum attempts: 5 before offering completion

### Session Management

**Session Timeout:**
- Active sessions: 30 minutes of inactivity
- Abandoned sessions: Marked as abandoned, not deleted
- Cleanup: Old sessions archived after 90 days

**Progress Persistence:**
- All attempts are saved regardless of outcome
- Progress can be resumed from any point
- Analytics available for improvement tracking

### Real-time Status Updates

**Frontend Uses Supabase Realtime:**
The frontend already has sophisticated Supabase Realtime implementation with existing hooks like `useRealtimeSubmission`, `useFeedbackWebSocket`, and `useClassDetailWebSocket`. The practice system follows the same proven patterns.

**Practice Session Realtime Implementation:**
```javascript
// Following existing frontend realtime patterns
const useRealtimePracticeSession = (sessionId) => {
  const dispatch = useDispatch();

  useEffect(() => {
    const channel = supabase
      .channel(`practice-session-${sessionId}`)
      .on('postgres_changes', {
        event: 'UPDATE',
        schema: 'public',
        table: 'practice_sessions',
        filter: `id=eq.${sessionId}`
      }, (payload) => {
        // Instant updates when backend changes database
        dispatch(updatePracticeSessionFromRealtime(payload.new));
        
        // Update UI based on new status
        updatePracticeUI(payload.new.status, payload.new);
      })
      .subscribe();

    return () => channel.unsubscribe();
  }, [sessionId]);
};

// Usage in practice components
const PracticeComponent = ({ sessionId }) => {
  const practiceSession = useRealtimePracticeSession(sessionId);
  
  // UI automatically updates on status changes
  switch(practiceSession.status) {
    case 'transcript_processing':
      return <ProcessingUI />;
    case 'practicing_sentences':
      return <SentenceRecordingUI session={practiceSession} />;
    case 'practicing_words':
      return <WordRecordingUI session={practiceSession} />;
    case 'practicing_full_transcript':
      return <FullTranscriptRecordingUI session={practiceSession} />;
    case 'completed':
      return <CompletionUI session={practiceSession} />;
  }
};
```

**Backend Responsibility:**
- **Update database only** → Supabase handles realtime broadcasting automatically
- **No custom websocket infrastructure** → Built into Supabase
- **No additional status endpoints** → Realtime provides instant updates
- **Focus on fast processing** → Database updates trigger immediate frontend updates

**Performance Benefits:**
- **Instant feedback** → 0.5-1 second response time (vs 3-5 seconds with polling)
- **Proven reliability** → Already working successfully for submission tracking
- **Consistent architecture** → Same patterns as existing realtime features
- **No server load** → No repeated HTTP requests needed

### Error Handling

**Transcription Failures:**
- Retry logic with exponential backoff
- Fallback to manual transcript entry
- User notification of processing delays

**Pronunciation Analysis Failures:**
- Retry failed analyses automatically
- Graceful degradation with simplified feedback
- Manual review option for edge cases

**Session Recovery:**
- Automatic session state recovery
- Progress preservation during network issues
- Conflict resolution for concurrent access

## Data Flow Summary

### Phase 1: Transcript Processing
1. **Transcript Session Creation**: User provides audio/transcript → Transcript session created with `recording_uploaded` status
2. **Transcription**: Audio converted to text → Status becomes `transcribing` 
3. **AI Improvement**: Transcript enhanced by AI → Status becomes `improving_transcript`
4. **Completion**: Improved transcript ready → Status becomes `transcript_ready`

### Phase 2: Pronunciation Practice
5. **Pronunciation Session Creation**: Linked to transcript session → Status becomes `ready_to_start`
6. **Sentence Extraction**: Improved transcript parsed into practice sentences → `sentences` array populated
7. **Webhook Activation**: Pronunciation session starts → Webhook session begins
8. **Sentence Practice Loop**: For each sentence:
   - Student records sentence → Status: `practicing_sentences`
   - Webhook analyzes pronunciation
   - Pass: Move to next sentence
   - Fail: Identify problematic words → Status: `practicing_words`
9. **Word Practice Loop**: For each problematic word:
   - Student records word
   - Webhook analyzes word pronunciation
   - Pass: Move to next word
   - Fail: Retry same word
10. **Sentence Retry**: After all words passed → Return to `practicing_sentences`, retry sentence
11. **Completion**: All sentences passed → Status: `completed`, webhook session ends

### Key Design Benefits
- **Clear Separation**: Two distinct phases with separate concerns and status tracking
- **Independent Scaling**: Phase 1 (async AI processing) and Phase 2 (real-time practice) can scale independently  
- **Better Error Handling**: Transcript processing failures don't affect pronunciation practice infrastructure
- **Flexible Workflow**: Students can pause between phases or restart pronunciation practice with existing transcripts
- **Comprehensive Tracking**: Full audit trail of both transcript processing and pronunciation attempts

This design provides a complete, scalable practice system that separates transcript processing from pronunciation practice while maintaining clear workflow progression and comprehensive tracking of all activities.