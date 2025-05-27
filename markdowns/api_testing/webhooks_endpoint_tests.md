# Webhooks Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/webhooks_endpoint.py` - Webhook endpoint implementations
- `app/pubsub/webhooks/submission_webhook.py` - Submission webhook handler
- `app/pubsub/webhooks/analysis_webhook.py` - Analysis webhook handler
- `app/models/schemas.py` - Webhook request/response models

## 1. Student Submission Webhook

### Scenario: Valid Student Submission
**Preconditions:**
- Mock SubmissionWebhook.handle_student_submission_webhook
- Valid Pub/Sub message format
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/webhooks/student-submission`
2. Include valid Pub/Sub payload:
   ```json
   {
     "message": {
       "data": "base64-encoded-submission-data",
       "messageId": "msg-123",
       "publishTime": "2024-01-01T00:00:00.000Z"
     }
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Response matches expected format
- `SubmissionWebhook.handle_student_submission_webhook` called
- Logging indicates parallel audio and transcription processing started
- Returns success status dictionary

### Scenario: Invalid Pub/Sub Message Format
**Preconditions:**
- Mock webhook handler
- Malformed Pub/Sub message
- Clean application state

**User Actions:**
1. Send POST request with invalid format:
   ```json
   {
     "invalid": "message format"
   }
   ```

**Expected Assertions:**
- HTTP status code 400 or 500
- Error handling in webhook handler
- Appropriate error response returned
- Error logged

## 2. Audio Conversion Done Webhook

### Scenario: Successful Audio Conversion
**Preconditions:**
- Mock AnalysisWebhook.handle_audio_conversion_done_webhook
- Valid audio conversion completion message
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/webhooks/audio-conversion-done`
2. Include valid conversion completion data

**Expected Assertions:**
- HTTP status code 200
- Analysis webhook handler called correctly
- Audio conversion completion logged
- Success response returned

### Scenario: Audio Conversion Error
**Preconditions:**
- Mock webhook handler to simulate conversion failure
- Error message from audio service
- Clean application state

**User Actions:**
1. Send POST request with conversion error data

**Expected Assertions:**
- HTTP status code 200 (webhook accepts error notifications)
- Error handling triggered in webhook
- Error status propagated correctly
- Failure logged appropriately

## 3. Transcription Done Webhook

### Scenario: Successful Transcription
**Preconditions:**
- Mock AnalysisWebhook.handle_transcription_done_webhook
- Valid transcription completion message
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/webhooks/transcription-done`
2. Include transcription results

**Expected Assertions:**
- HTTP status code 200
- Transcription webhook handler called
- Transcription completion logged
- Success response returned

### Scenario: Transcription Service Failure
**Preconditions:**
- Mock webhook handler for transcription failure
- Error message from transcription service
- Clean application state

**User Actions:**
1. Send POST request with transcription error

**Expected Assertions:**
- HTTP status code 200
- Error handled gracefully
- Failure status propagated
- Error logged with details

## 4. Analysis Service Webhooks

### Scenario: Question Analysis Ready
**Preconditions:**
- Mock AnalysisWebhook.handle_question_analysis_ready_webhook
- Valid analysis ready message
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/webhooks/question-analysis-ready`

**Expected Assertions:**
- HTTP status code 200
- Question analysis ready handler called
- Processing continuation triggered
- Success response returned

### Scenario: Fluency Analysis Complete
**Preconditions:**
- Mock AnalysisWebhook.handle_fluency_done_webhook
- Valid fluency analysis results
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/webhooks/fluency-done`

**Expected Assertions:**
- HTTP status code 200
- Fluency analysis completion handled
- Results processed correctly
- Success status returned

### Scenario: Grammar Analysis Complete
**Preconditions:**
- Mock AnalysisWebhook.handle_grammar_done_webhook
- Valid grammar analysis results
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/webhooks/grammar-done`

**Expected Assertions:**
- HTTP status code 200
- Grammar analysis completion handled
- Results integrated correctly
- Success response returned

### Scenario: Lexical Analysis Complete
**Preconditions:**
- Mock AnalysisWebhook.handle_lexical_done_webhook
- Valid lexical analysis results
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/webhooks/lexical-done`

**Expected Assertions:**
- HTTP status code 200
- Lexical analysis completion handled
- Vocabulary analysis results processed
- Success status returned

## 5. Pronunciation Done Webhook (Fluency Trigger)

### Scenario: Pronunciation Analysis Triggers Fluency
**Preconditions:**
- Mock AnalysisWebhook.handle_pronunciation_done_webhook
- Valid pronunciation analysis results
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/webhooks/pronunciation-done`
2. Include pronunciation analysis data

**Expected Assertions:**
- HTTP status code 200
- Pronunciation analysis handled
- Fluency analysis triggered (Phase 2)
- Fluency processing initiated
- Success response with fluency trigger confirmation

### Scenario: Pronunciation Analysis Error
**Preconditions:**
- Mock webhook handler for pronunciation error
- Error from pronunciation service
- Clean application state

**User Actions:**
1. Send POST request with pronunciation error data

**Expected Assertions:**
- HTTP status code 200
- Error handled gracefully
- Fluency analysis may still be triggered with error status
- Error propagation working correctly

## 6. Analysis Complete Webhooks

### Scenario: Individual Analysis Complete
**Preconditions:**
- Mock AnalysisWebhook.handle_analysis_complete_webhook
- Valid analysis completion data
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/webhooks/analysis-complete`

**Expected Assertions:**
- HTTP status code 200
- Analysis completion handled
- Results aggregation triggered
- Final processing initiated

### Scenario: Submission Analysis Complete
**Preconditions:**
- Mock AnalysisWebhook.handle_submission_analysis_complete_webhook
- Complete submission analysis data
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/webhooks/submission-analyis-complete`

**Expected Assertions:**
- HTTP status code 200
- Complete submission analysis handled
- All questions processed
- Final submission status updated
- Grade calculation triggered

## 7. Webhook Request Processing

### Scenario: Concurrent Webhook Processing
**Preconditions:**
- Mock all webhook handlers
- Multiple simultaneous webhook calls
- Clean application state

**User Actions:**
1. Send multiple webhook requests simultaneously
2. Mix different webhook types

**Expected Assertions:**
- All requests processed successfully
- No race conditions
- Proper request isolation
- Consistent response times

### Scenario: Request Timeout Handling
**Preconditions:**
- Mock webhook handler with processing delay
- Timeout configuration
- Clean application state

**User Actions:**
1. Send webhook request that triggers long processing

**Expected Assertions:**
- Request handled within timeout limits
- No hanging connections
- Appropriate timeout response if exceeded
- Resource cleanup on timeout

## 8. Error Handling and Recovery

### Scenario: Webhook Handler Exception
**Preconditions:**
- Mock webhook handler to raise exception
- Valid request data
- Clean application state

**User Actions:**
1. Send valid webhook request
2. Handler raises unexpected exception

**Expected Assertions:**
- HTTP status code 500
- Exception handled gracefully
- Error logged with full context
- No data corruption
- System remains stable

### Scenario: Malformed Request Body
**Preconditions:**
- Mock webhook handlers
- Invalid JSON or request format
- Clean application state

**User Actions:**
1. Send webhook request with malformed body

**Expected Assertions:**
- HTTP status code 400
- JSON parsing error handled
- Appropriate error response
- No webhook handler called

## 9. Logging and Monitoring

### Scenario: Webhook Processing Logging
**Preconditions:**
- Mock all webhook handlers
- Logging configuration enabled
- Clean application state

**User Actions:**
1. Send various webhook requests

**Expected Assertions:**
- Each webhook type logged appropriately
- Processing start/completion logged
- Error cases logged with details
- Performance metrics captured
- Log levels appropriate for each scenario

## Integration Points to Verify

1. **Webhook Handler Integration**
   - Proper handler instantiation and dependency injection
   - Request routing to correct handlers
   - Response format consistency
   - Error propagation between layers

2. **Pub/Sub Message Processing**
   - Message format validation
   - Base64 decoding working correctly
   - Message ordering handled appropriately
   - Duplicate message handling

3. **Analysis Pipeline Coordination**
   - Webhook sequence ordering
   - State transitions between analysis phases
   - Data consistency across webhook calls
   - Final result aggregation working

4. **Error Recovery**
   - Failed webhook retry mechanisms
   - Partial failure handling
   - System stability under error conditions
   - Data integrity maintenance 