# Submission Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/submission_endpoint.py` - Submission endpoint implementation
- `app/models/submission_model.py` - Request/response models
- `app/services/submission_service.py` - Submission processing service
- `app/core/config.py` - Configuration and dependencies

## 1. Direct Frontend Submission

### Scenario: Valid Audio Submission
**Preconditions:**
- Mock SubmissionService
- Valid audio URLs in request
- Clean application state
- Mock Pub/Sub client

**User Actions:**
1. Send POST request to `/api/v1/submission/submit`
2. Include valid payload:
   ```json
   {
     "audio_urls": ["https://example.com/audio1.mp3"],
     "submission_url": "test-submission-123",
     "total_questions": 1
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Response matches `SubmissionResponse` schema
- `SubmissionService.process_submission` called with correct parameters
- Request body parsed as `SubmissionRequest` model
- No base64 decoding attempted

### Scenario: Multiple Audio Files
**Preconditions:**
- Mock SubmissionService
- Multiple valid audio URLs
- Clean application state

**User Actions:**
1. Send POST request with multiple audio files:
   ```json
   {
     "audio_urls": [
       "https://example.com/audio1.mp3",
       "https://example.com/audio2.wav", 
       "https://example.com/audio3.webm"
     ],
     "submission_url": "multi-audio-test",
     "total_questions": 3
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- All audio URLs processed
- Response contains processing status for all files
- Submission service receives complete audio URL array

### Scenario: Invalid Request Payload
**Preconditions:**
- Mock SubmissionService
- Clean application state

**User Actions:**
1. Send POST request with invalid payload:
   ```json
   {
     "audio_urls": [],
     "submission_url": "",
     "total_questions": 0
   }
   ```

**Expected Assertions:**
- HTTP status code 422 (Validation Error)
- Pydantic validation error response
- `SubmissionService.process_submission` not called
- Error details specify validation failures

## 2. Pub/Sub Push Message Handling

### Scenario: Valid Pub/Sub Message
**Preconditions:**
- Mock SubmissionService
- Valid base64 encoded message data
- Clean application state

**User Actions:**
1. Send POST request with Pub/Sub format:
   ```json
   {
     "message": {
       "data": "eyJhdWRpb191cmxzIjpbImh0dHBzOi8vZXhhbXBsZS5jb20vYXVkaW8ubXAzIl0sInN1Ym1pc3Npb25fdXJsIjoidGVzdCIsInRvdGFsX3F1ZXN0aW9ucyI6MX0=",
       "messageId": "123456",
       "publishTime": "2024-01-01T00:00:00.000Z"
     }
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Base64 data decoded correctly
- JSON parsed from decoded data
- `SubmissionRequest` model created from decoded data
- `SubmissionService.process_submission` called with decoded parameters

### Scenario: Invalid Base64 Data
**Preconditions:**
- Mock SubmissionService
- Malformed base64 data
- Clean application state

**User Actions:**
1. Send POST request with invalid base64:
   ```json
   {
     "message": {
       "data": "invalid-base64-data!@#",
       "messageId": "123456"
     }
   }
   ```

**Expected Assertions:**
- HTTP status code 400 or 500
- Base64 decoding error handled
- Error response with appropriate message
- `SubmissionService.process_submission` not called

### Scenario: Invalid JSON in Pub/Sub Data
**Preconditions:**
- Mock SubmissionService
- Valid base64 encoding invalid JSON
- Clean application state

**User Actions:**
1. Send POST request with base64 encoded invalid JSON:
   ```json
   {
     "message": {
       "data": "aW52YWxpZC1qc29u", // base64 for "invalid-json"
       "messageId": "123456"
     }
   }
   ```

**Expected Assertions:**
- HTTP status code 400 or 500
- JSON parsing error handled
- Error response with appropriate message
- `SubmissionService.process_submission` not called

## 3. Service Integration

### Scenario: Service Processing Success
**Preconditions:**
- Mock successful `SubmissionService.process_submission`
- Valid request data
- Clean application state

**User Actions:**
1. Send valid submission request
2. Service returns successful response

**Expected Assertions:**
- HTTP status code 200
- Response contains success status
- Service method called exactly once
- Response matches expected `SubmissionResponse` schema

### Scenario: Service Processing Failure
**Preconditions:**
- Mock `SubmissionService.process_submission` to raise exception
- Valid request data
- Clean application state

**User Actions:**
1. Send valid submission request
2. Service raises processing exception

**Expected Assertions:**
- HTTP status code 500
- Error response returned
- Exception handled gracefully
- Error message contains relevant details

## 4. Request Format Detection

### Scenario: Pub/Sub vs Direct Request Detection
**Preconditions:**
- Mock SubmissionService
- Clean application state

**User Actions:**
1. Send direct request (no "message" field)
2. Send Pub/Sub request (with "message" field)

**Expected Assertions:**
- Direct request: No base64 decoding attempted
- Pub/Sub request: Base64 decoding performed
- Both requests result in same service call
- Correct request type detected and handled

## Integration Points to Verify

1. **Request Parsing Flow**
   - Raw request → Format detection → Data extraction → Model validation
   - Error handling at each parsing stage
   - Consistent response format regardless of input format

2. **Service Integration**
   - Dependency injection working correctly
   - Service method called with proper parameters
   - Service response mapped to API response

3. **Model Validation**
   - Pydantic model validation enforced
   - Validation errors returned with proper HTTP status
   - Required fields enforced correctly 