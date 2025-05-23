# Pub/Sub Push-Based Migration Guide

## Overview

The system has been migrated from a **pull-based** to a **push-based** Google Cloud Pub/Sub architecture. This change improves scalability, reduces latency, and eliminates the need for continuous polling.

## Architecture Changes

### Before (Pull-Based)
```
Application → Polls Pub/Sub → Processes Messages
```

### After (Push-Based)
```
Pub/Sub → Pushes to Webhooks → Application Processes
```

## New Flow

### 1. Student Submission Entry Point
```
POST /api/v1/submission/submit
↓
Publishes to: student-submission-topic
↓ (Push to webhooks)
Two parallel processing streams:
├── /webhooks/student-submission-audio
└── /webhooks/student-submission-transcription
```

### 2. Audio Processing Stream
```
Audio Webhook → AudioService → Publishes to: audio-conversion-done-topic
↓ (Push to webhook)
/webhooks/audio-conversion-done → AnalysisCoordinator
```

### 3. Transcription Processing Stream
```
Transcription Webhook → TranscriptionService → Publishes to: transcription-done-topic
↓ (Push to webhook)
/webhooks/transcription-done → AnalysisCoordinator
```

### 4. Analysis Coordination
```
AnalysisCoordinator (waits for both audio + transcription)
↓
Publishes to: question-analysis-ready-topic
↓ (Push to webhook)
/webhooks/question-analysis-ready → Runs all analysis services
```

### 5. Individual Analysis Services
```
Question Ready Webhook → Parallel execution:
├── PronunciationService → pronoun-done-topic
├── GrammarService → grammer-done-topic
├── LexicalService → lexical-done-topic
└── FluencyService → fluency-done-topic
↓
All complete → analysis-complete-topic
```

## Webhook Endpoints

| Endpoint | Triggered By | Purpose |
|----------|-------------|---------|
| `/webhooks/student-submission-audio` | `student-submission-topic` | Audio processing |
| `/webhooks/student-submission-transcription` | `student-submission-topic` | Transcription processing |
| `/webhooks/audio-conversion-done` | `audio-conversion-done-topic` | Audio completion |
| `/webhooks/transcription-done` | `transcription-done-topic` | Transcription completion |
| `/webhooks/question-analysis-ready` | `question-analysis-ready-topic` | Start analysis |
| `/webhooks/fluency-done` | `fluency-done-topic` | Fluency completion |
| `/webhooks/grammar-done` | `grammer-done-topic` | Grammar completion |
| `/webhooks/lexical-done` | `lexical-done-topic` | Lexical completion |
| `/webhooks/pronunciation-done` | `pronoun-done-topic` | Pronunciation completion |
| `/webhooks/analysis-complete` | `analysis-complete-topic` | Final completion |

## Topics and Subscriptions

### Topics
```python
TOPICS = {
    "ANALYSIS_COMPLETE": "analysis-complete-topic",
    "AUDIO_CONVERSION_DONE": "audio-conversion-done-topic",
    "FLUENCY_DONE": "fluency-done-topic",
    "GRAMMER_DONE": "grammer-done-topic",
    "LEXICAL_DONE": "lexical-done-topic",
    "PRONOUN_DONE": "pronoun-done-topic",
    "QUESTION_ANALYSIS_READY": "question-analysis-ready-topic",
    "STUDENT_SUBMISSION": "student-submission-topic",
    "TRANSCRIPTION_DONE": "transcription-done-topic"
}
```

### Required Subscriptions (Push Config)
You need to configure these subscriptions in Google Cloud Console with push endpoints:

```bash
# Student submission (needs 2 subscriptions for parallel processing)
student-submission-topic-audio-sub → https://your-domain.com/api/v1/webhooks/student-submission-audio
student-submission-topic-transcription-sub → https://your-domain.com/api/v1/webhooks/student-submission-transcription

# Processing results
audio-conversion-service-sub → https://your-domain.com/api/v1/webhooks/audio-conversion-done
transcription-service-sub → https://your-domain.com/api/v1/webhooks/transcription-done

# Analysis coordination
question-analysis-ready-topic-sub → https://your-domain.com/api/v1/webhooks/question-analysis-ready

# Individual analysis completions
fluency-done-topic-sub → https://your-domain.com/api/v1/webhooks/fluency-done
grammer-done-topic-sub → https://your-domain.com/api/v1/webhooks/grammar-done
lexical-done-topic-sub → https://your-domain.com/api/v1/webhooks/lexical-done
pronoun-done-topic-sub → https://your-domain.com/api/v1/webhooks/pronunciation-done

# Final completion
analysis-complete-topic-sub → https://your-domain.com/api/v1/webhooks/analysis-complete
```

## Configuration

### Environment Variables
```bash
# Required
BASE_WEBHOOK_URL=https://your-app-domain.com
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Optional (for webhook authentication)
PUBSUB_WEBHOOK_AUTH_TOKEN=your-secret-token
```

### Google Cloud Pub/Sub Setup

1. **Create Topics** (if not exists):
```bash
gcloud pubsub topics create student-submission-topic
gcloud pubsub topics create audio-conversion-done-topic
gcloud pubsub topics create transcription-done-topic
gcloud pubsub topics create question-analysis-ready-topic
gcloud pubsub topics create fluency-done-topic
gcloud pubsub topics create grammer-done-topic
gcloud pubsub topics create lexical-done-topic
gcloud pubsub topics create pronoun-done-topic
gcloud pubsub topics create analysis-complete-topic
```

2. **Create Push Subscriptions**:
```bash
# Student submission (parallel processing)
gcloud pubsub subscriptions create student-submission-topic-audio-sub \
  --topic=student-submission-topic \
  --push-endpoint=https://your-domain.com/api/v1/webhooks/student-submission-audio

gcloud pubsub subscriptions create student-submission-topic-transcription-sub \
  --topic=student-submission-topic \
  --push-endpoint=https://your-domain.com/api/v1/webhooks/student-submission-transcription

# Audio and transcription results
gcloud pubsub subscriptions create audio-conversion-service-sub \
  --topic=audio-conversion-done-topic \
  --push-endpoint=https://your-domain.com/api/v1/webhooks/audio-conversion-done

gcloud pubsub subscriptions create transcription-service-sub \
  --topic=transcription-done-topic \
  --push-endpoint=https://your-domain.com/api/v1/webhooks/transcription-done

# Analysis ready
gcloud pubsub subscriptions create question-analysis-ready-topic-sub \
  --topic=question-analysis-ready-topic \
  --push-endpoint=https://your-domain.com/api/v1/webhooks/question-analysis-ready

# Individual analysis completions
gcloud pubsub subscriptions create fluency-done-topic-sub \
  --topic=fluency-done-topic \
  --push-endpoint=https://your-domain.com/api/v1/webhooks/fluency-done

gcloud pubsub subscriptions create grammer-done-topic-sub \
  --topic=grammer-done-topic \
  --push-endpoint=https://your-domain.com/api/v1/webhooks/grammar-done

gcloud pubsub subscriptions create lexical-done-topic-sub \
  --topic=lexical-done-topic \
  --push-endpoint=https://your-domain.com/api/v1/webhooks/lexical-done

gcloud pubsub subscriptions create pronoun-done-topic-sub \
  --topic=pronoun-done-topic \
  --push-endpoint=https://your-domain.com/api/v1/webhooks/pronunciation-done

gcloud pubsub subscriptions create analysis-complete-topic-sub \
  --topic=analysis-complete-topic \
  --push-endpoint=https://your-domain.com/api/v1/webhooks/analysis-complete
```

## Key Benefits

1. **Real-time Processing**: No polling delays
2. **Better Scalability**: Automatic scaling based on message volume
3. **Lower Latency**: Immediate webhook triggers
4. **Resource Efficiency**: No continuous polling overhead
5. **Parallel Processing**: Student submissions trigger both audio and transcription processing simultaneously

## Security

- Webhook endpoints support authentication tokens via `PUBSUB_WEBHOOK_AUTH_TOKEN`
- All webhook calls include Pub/Sub message validation
- Base64 encoded message data with automatic parsing

## Monitoring

- All webhook calls are logged with detailed information
- Error handling with proper HTTP status codes
- Message acknowledgment handled automatically by Pub/Sub push

## Troubleshooting

1. **Webhooks not receiving messages**: Check subscription push endpoint URLs
2. **Authentication errors**: Verify `PUBSUB_WEBHOOK_AUTH_TOKEN` configuration
3. **Message format errors**: Check Pub/Sub message structure in logs
4. **Parallel processing issues**: Verify both audio and transcription subscriptions are configured

## Migration Notes

- **Removed**: Pull-based `SubscriberHandler.start_listening()` method
- **Removed**: `PubSubClient.pull_messages()` method
- **Added**: Webhook handlers for all message types
- **Added**: Push message parsing utilities
- **Updated**: All services to use `publish_message_by_name()` method

The system now operates entirely on push-based webhooks, eliminating the need for background polling tasks. 