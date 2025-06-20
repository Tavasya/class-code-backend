# Pub/Sub Messaging Architecture

## 🚀 Overview

The Audio Analysis API uses Google Cloud Pub/Sub for asynchronous message passing between services. This enables loose coupling, scalability, and reliable processing of audio analysis workflows.

## 📋 Topic and Subscription Configuration

**File**: `app/pubsub/topics_subs.py`

### Topics Defined:
```python
TOPICS = {
    "ANALYSIS_COMPLETE": "analysis-complete-topic",
    "AUDIO_CONVERSION_DONE": "audio-conversion-done-topic", 
    "FLUENCY_DONE": "fluency-done-topic",
    "GRAMMER_DONE": "grammer-done-topic",
    "LEXICAL_DONE": "lexical-done-topic",
    "PRONUNCIATION_DONE": "pronoun-done-topic",
    "QUESTION_ANALYSIS_READY": "question-analysis-ready-topic",
    "STUDENT_SUBMISSION": "student-submission-topic",
    "SUBMISSION_ANALYSIS_COMPLETE": "submission-analyis-complete-topic",
    "TRANSCRIPTION_DONE": "transcription-done-topic",
    "VOCABULARY_DONE": "vocabulary-done-topic"
}
```

### Corresponding Subscriptions:
```python
SUBSCRIPTIONS = {
    "ANALYSIS_COMPLETE": "analysis-complete-topic-sub",
    "AUDIO_CONVERSION_DONE": "audio-conversion-service-sub",
    "FLUENCY_DONE": "fluency-done-topic-sub",
    "GRAMMER_DONE": "grammer-done-topic-sub", 
    "LEXICAL_DONE": "lexical-done-topic-sub",
    "PRONUNCIATION_DONE": "pronoun-done-topic-sub",
    "QUESTION_ANALYSIS_READY": "question-analysis-ready-topic-sub",
    "STUDENT_SUBMISSION": "student-submission-topic-sub",
    "SUBMISSION_ANALYSIS_COMPLETE": "submission-analyis-complete-topic-sub",
    "TRANSCRIPTION_DONE": "transcription-service-sub",
    "VOCABULARY_DONE": "vocabulary-done-topic-sub"
}
```

## 🔧 Pub/Sub Client Implementation

**File**: `app/pubsub/client.py`

### Key Features:
- **Topic Management**: Automatic topic creation and validation
- **Message Publishing**: JSON serialization and error handling
- **Subscription Management**: Pull-based message consumption
- **Error Handling**: Comprehensive logging and retry logic

### Core Methods:
```python
class PubSubClient:
    def publish_message_by_name(topic_name: str, message: dict)
    def create_topic_if_not_exists(topic_name: str)
    def create_subscription_if_not_exists(topic_name: str, subscription_name: str)
    def pull_messages(subscription_name: str, max_messages: int)
```

## 📨 Message Flow Patterns

### 1. **Fan-Out Pattern** 
**Student Submission → Multiple Processing Services**

```
STUDENT_SUBMISSION Topic
    ├─ AudioService (converts to WAV)
    └─ TranscriptionService (converts to text)
```

### 2. **Coordination Pattern**
**Analysis Coordinator → Multiple Analysis Services**

```
QUESTION_ANALYSIS_READY Topic
    ├─ PronunciationService
    ├─ FluencyService  
    ├─ GrammarService
    ├─ LexicalService
    └─ VocabularyService
```

### 3. **Aggregation Pattern**
**Multiple Analysis Results → Database Service**

```
Analysis Done Topics → DatabaseService
    ├─ PRONUNCIATION_DONE
    ├─ FLUENCY_DONE
    ├─ GRAMMER_DONE
    ├─ LEXICAL_DONE
    └─ VOCABULARY_DONE
```

## 🔄 Message Lifecycle

### Publishing Flow:
1. Service creates message object
2. Serializes to JSON
3. Publishes to specific topic
4. Receives message ID confirmation
5. Logs success/failure

### Consumption Flow:
1. Service subscribes to topic
2. Pulls messages from subscription
3. Processes message content
4. Acknowledges successful processing
5. Publishes results to next topic

## 📊 Message Schemas

### Student Submission Message:
```json
{
  "audio_url": "https://example.com/audio.mp3",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123",
  "total_questions": 5
}
```

### Audio Conversion Done Message:
```json
{
  "wav_path": "/tmp/session_123/audio_1.wav",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123",
  "original_audio_url": "https://example.com/audio.mp3",
  "session_id": "session_123",
  "total_questions": 5
}
```

### Transcription Done Message:
```json
{
  "text": "This is the transcribed text...",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123",
  "audio_url": "https://example.com/audio.mp3",
  "error": null,
  "total_questions": 5
}
```

### Question Analysis Ready Message:
```json
{
  "wav_path": "/tmp/session_123/audio_1.wav",
  "transcript": "This is the transcribed text...",
  "question_number": 1,
  "submission_url": "https://frontend.com/submission/123",
  "audio_url": "https://example.com/audio.mp3",
  "session_id": "session_123",
  "total_questions": 5
}
```

### Analysis Result Messages:
```json
{
  "submission_url": "https://frontend.com/submission/123",
  "question_number": 1,
  "analysis_type": "pronunciation",
  "results": {
    "overall_score": 85.5,
    "detailed_scores": {...},
    "feedback": "..."
  },
  "total_questions": 5
}
```

### Submission Analysis Complete Message:
```json
{
  "submission_url": "https://frontend.com/submission/123",
  "overall_score": 82.3,
  "question_scores": [...],
  "analysis_summary": {...},
  "completed_at": "2024-01-15T10:30:00Z"
}
```

## 🔗 Webhook Integration

**File**: `app/pubsub/webhooks/`

### Webhook Handler:
- Listens to `SUBMISSION_ANALYSIS_COMPLETE` topic
- Makes HTTP POST to frontend webhook URL
- Includes retry logic for failed deliveries
- Logs webhook delivery status

## 🏗️ Service Integration

### Core Services and Their Pub/Sub Usage:

#### SubmissionService:
- **Publishes to**: `STUDENT_SUBMISSION`
- **Message**: Individual audio processing requests

#### AudioService:
- **Subscribes to**: `STUDENT_SUBMISSION`
- **Publishes to**: `AUDIO_CONVERSION_DONE`
- **Process**: Downloads and converts audio files

#### TranscriptionService:
- **Subscribes to**: `STUDENT_SUBMISSION`
- **Publishes to**: `TRANSCRIPTION_DONE`
- **Process**: Converts speech to text

#### AnalysisCoordinatorService:
- **Subscribes to**: `AUDIO_CONVERSION_DONE`, `TRANSCRIPTION_DONE`
- **Publishes to**: `QUESTION_ANALYSIS_READY`
- **Process**: Coordinates when both audio and transcript are ready

#### Analysis Services (Pronunciation, Fluency, Grammar, Lexical, Vocabulary):
- **Subscribes to**: `QUESTION_ANALYSIS_READY`
- **Publishes to**: Respective `*_DONE` topics
- **Process**: Performs specific analysis

#### DatabaseService:
- **Subscribes to**: All `*_DONE` analysis topics
- **Publishes to**: `SUBMISSION_ANALYSIS_COMPLETE`
- **Process**: Stores results and aggregates final scores

## ⚙️ Configuration

### Environment Variables:
```bash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

### Topic/Subscription Creation:
- Automatically creates topics if they don't exist
- Creates pull subscriptions for each service
- Handles Google Cloud Pub/Sub authentication

## 🔍 Monitoring and Debugging

### Logging:
- All message publishing logged with message IDs
- Subscription pull operations logged
- Error handling with detailed stack traces
- Message processing time tracking

### Error Handling:
- Dead letter queues for failed messages
- Exponential backoff for retries
- Message deduplication handling
- Graceful degradation for service failures

## 🚀 Scalability Features

### Horizontal Scaling:
- Multiple instances can subscribe to same subscription
- Load balancing handled by Pub/Sub
- Services can scale independently

### Message Durability:
- Messages persisted until acknowledged
- Automatic retry for unacknowledged messages
- Configurable acknowledgment deadlines

### Performance Optimization:
- Batch message publishing
- Concurrent message processing
- Configurable pull message limits

## 🔧 Development and Testing

### Local Development:
- Pub/Sub emulator support
- Mock message publishing for testing
- Subscription simulation tools

### Testing Strategy:
- Unit tests for message serialization
- Integration tests for end-to-end flows
- Mock Pub/Sub client for isolated testing

## 📈 Future Enhancements

### Potential Improvements:
1. **Message Schema Validation**: JSON Schema validation for all messages
2. **Message Ordering**: Ordered processing for related messages
3. **Metrics Collection**: Pub/Sub message metrics and monitoring
4. **Circuit Breakers**: Automatic failure detection and recovery
5. **Message Encryption**: End-to-end message encryption for sensitive data 