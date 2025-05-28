# Transcription Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/transcription_endpoint.py` - Transcription endpoint implementation
- `app/models/transcription_model.py` - Request/response models
- `app/services/transcription_service.py` - Transcription processing service
- `app/main.py` - FastAPI application instance

## Test Setup
- Uses `TestClient` from FastAPI for endpoint testing
- Mocks `TranscriptionService` with `AsyncMock` for `process_single_transcription` method
- All tests use the endpoint `/api/v1/transcription/audio_proccessing`

## 1. Direct Transcription Request

### Scenario: Valid Transcription Request with Submission URL
**Test Method:** `test_direct_transcription_request_success`
**Preconditions:**
- Mock TranscriptionService.process_single_transcription returns success response
- Valid audio URL, question number, and submission URL
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/transcription/audio_proccessing`
2. Include valid payload:
   ```json
   {
     "audio_url": "https://example.com/speech.mp3",
     "question_number": 1,
     "submission_url": "test-submission-123"
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Response data contains: `"text": "Hello world, this is a test transcription."`
- Response data contains: `"error": None`
- Response data contains: `"question_number": 1`
- `TranscriptionService.process_single_transcription` called once with parameters: `("https://example.com/speech.mp3", 1, "test-submission-123")`

### Scenario: Transcription Without Submission URL
**Test Method:** `test_direct_transcription_without_submission_url`
**Preconditions:**
- Mock TranscriptionService.process_single_transcription returns success response
- Valid audio URL and question number, no submission URL
- Clean application state

**User Actions:**
1. Send POST request without submission_url:
   ```json
   {
     "audio_url": "https://example.com/speech.wav",
     "question_number": 2
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Response data contains: `"text": "Test transcription without submission URL."`
- Response data contains: `"question_number": 2`
- Service called with None for submission_url parameter: `("https://example.com/speech.wav", 2, None)`

## 2. Pub/Sub Message Processing

### Scenario: Valid Pub/Sub Transcription Message
**Test Method:** `test_pubsub_transcription_message_success`
**Preconditions:**
- Mock TranscriptionService.process_single_transcription returns success response
- Valid base64 encoded Pub/Sub message with proper JSON structure
- Clean application state

**User Actions:**
1. Create base64 encoded message data:
   ```json
   {
     "audio_url": "https://example.com/speech.mp3",
     "question_number": 1,
     "submission_url": "test-submission"
   }
   ```
2. Send POST request with Pub/Sub format:
   ```json
   {
     "message": {
       "data": "base64_encoded_data",
       "messageId": "transcription-msg-123",
       "publishTime": "2024-01-01T00:00:00.000Z"
     }
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Response data contains: `"text": "Pub/Sub transcription successful."`
- Response data contains: `"question_number": 1`
- Base64 data decoded and JSON parsed correctly
- TranscriptionService called with decoded parameters: `("https://example.com/speech.mp3", 1, "test-submission")`

### Scenario: Invalid Base64 in Pub/Sub Message
**Test Method:** `test_pubsub_invalid_base64_data`
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Malformed base64 data that cannot be decoded
- Clean application state

**User Actions:**
1. Send POST request with invalid base64:
   ```json
   {
     "message": {
       "data": "invalid-base64-data!@#$",
       "messageId": "transcription-msg-456"
     }
   }
   ```

**Expected Assertions:**
- HTTP status code 500
- Response contains error message: `"Failed to process audio"` in detail
- Base64 decoding error handled gracefully
- TranscriptionService.process_single_transcription not called

### Scenario: Invalid JSON in Pub/Sub Data
**Test Method:** `test_pubsub_invalid_json_data`
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Valid base64 encoding but invalid JSON content
- Clean application state

**User Actions:**
1. Create base64 encoded invalid JSON: `"invalid-json-content"`
2. Send POST request with encoded invalid JSON:
   ```json
   {
     "message": {
       "data": "aW52YWxpZC1qc29uLWNvbnRlbnQ=",
       "messageId": "transcription-msg-789"
     }
   }
   ```

**Expected Assertions:**
- HTTP status code 500
- Response contains error message: `"Failed to process audio"` in detail
- JSON parsing error handled gracefully
- TranscriptionService.process_single_transcription not called

## 3. Transcription Service Integration

### Scenario: Transcription Service Processing Failure
**Test Method:** `test_transcription_service_failure`
**Preconditions:**
- Mock TranscriptionService.process_single_transcription to raise Exception("Transcription failed")
- Valid request data
- Clean application state

**User Actions:**
1. Send valid transcription request:
   ```json
   {
     "audio_url": "https://example.com/speech.mp3",
     "question_number": 1,
     "submission_url": "test-submission"
   }
   ```

**Expected Assertions:**
- HTTP status code 500
- Response contains exact error message: `"Failed to process audio: Transcription failed"`
- Exception properly caught and handled
- Error details include service exception message

### Scenario: Service Returns Error Response
**Test Method:** `test_transcription_with_error_from_service`
**Preconditions:**
- Mock TranscriptionService.process_single_transcription returns error response
- Valid request data
- Clean application state

**User Actions:**
1. Send request with poor quality audio:
   ```json
   {
     "audio_url": "https://example.com/poor_quality.mp3",
     "question_number": 1,
     "submission_url": "test-submission"
   }
   ```

**Expected Assertions:**
- HTTP status code 200 (service handles error gracefully)
- Response data contains: `"text": ""`
- Response data contains: `"error": "Audio quality too poor for transcription"`
- Response data contains: `"question_number": 1`
- Service error properly passed through to response

## 4. Parameter Validation

### Scenario: Missing Audio URL
**Test Method:** `test_missing_audio_url`
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Request missing required audio_url field
- Clean application state

**User Actions:**
1. Send POST request without audio_url:
   ```json
   {
     "question_number": 1,
     "submission_url": "test"
   }
   ```

**Expected Assertions:**
- HTTP status code 500
- Response contains error message: `"Failed to process audio"` in detail
- KeyError handled in exception block
- TranscriptionService.process_single_transcription not called

### Scenario: Missing Question Number
**Test Method:** `test_missing_question_number`
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Request missing required question_number field
- Clean application state

**User Actions:**
1. Send POST request without question_number:
   ```json
   {
     "audio_url": "https://example.com/speech.mp3",
     "submission_url": "test"
   }
   ```

**Expected Assertions:**
- HTTP status code 500
- Response contains error message: `"Failed to process audio"` in detail
- KeyError handled in exception block
- TranscriptionService.process_single_transcription not called

## 5. Audio Format Support

### Scenario: Different Audio File Formats
**Test Method:** `test_different_audio_formats`
**Preconditions:**
- Mock TranscriptionService.process_single_transcription for multiple formats
- Various audio file URLs with different extensions
- Clean application state

**User Actions:**
1. Test with different audio formats:
   - `"https://example.com/speech.mp3"` (question_number: 1)
   - `"https://example.com/speech.wav"` (question_number: 2)
   - `"https://example.com/speech.webm"` (question_number: 3)
   - `"https://example.com/speech.m4a"` (question_number: 4)

**Expected Assertions:**
- All requests return HTTP status code 200
- Each response contains format-specific text: `"Transcription for format {i}"`
- Each response contains correct question_number
- Service called with correct URLs for each format
- All formats processed consistently

## 6. Response Format Validation

### Scenario: Complete TranscriptionResponse Schema
**Test Method:** `test_response_format_validation`
**Preconditions:**
- Mock successful TranscriptionService response
- Valid transcription request
- Clean application state

**User Actions:**
1. Send valid request:
   ```json
   {
     "audio_url": "https://example.com/speech.mp3",
     "question_number": 5,
     "submission_url": "test-submission"
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Response contains all required fields: `"text"`, `"error"`, `"question_number"`
- Field type validation:
  - `data["text"]` is string type
  - `data["error"]` is None or string type
  - `data["question_number"]` is None or integer type
- Response data contains: `"text": "Valid transcription response"`
- Response data contains: `"question_number": 5`

## 7. Logging and Monitoring

### Scenario: Successful Processing Logging
**Test Method:** `test_logging_on_success`
**Preconditions:**
- Mock logger from transcription_endpoint module
- Mock successful TranscriptionService response
- Valid transcription request

**User Actions:**
1. Send valid transcription request:
   ```json
   {
     "audio_url": "https://example.com/speech.mp3",
     "question_number": 1,
     "submission_url": "test-submission"
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Logger.info called with exact message: `"Transcribing audio URL for question 1"`
- Processing logged appropriately for question number
- No sensitive data logged

### Scenario: Error Processing Logging
**Test Method:** `test_logging_on_error`
**Preconditions:**
- Mock logger from transcription_endpoint module
- Mock TranscriptionService to raise Exception("Service error")
- Valid request triggering error

**User Actions:**
1. Send request that triggers service exception:
   ```json
   {
     "audio_url": "https://example.com/speech.mp3",
     "question_number": 1,
     "submission_url": "test-submission"
   }
   ```

**Expected Assertions:**
- HTTP status code 500
- Logger.exception called exactly once
- Error logged with full context and stack trace
- Exception details available for debugging

## Integration Points Verified

1. **Request Processing Flow**
   - Direct request format detection (no "message" field)
   - Pub/Sub request format detection (with "message" field)
   - Base64 decoding for Pub/Sub messages
   - JSON parsing from decoded data
   - Parameter extraction and validation

2. **TranscriptionService Integration**
   - Service instantiation through dependency injection
   - Async method call: `process_single_transcription(audio_url, question_number, submission_url)`
   - Response mapping from service to API response
   - Error propagation and handling

3. **Error Handling**
   - Base64 decoding errors → 500 status with "Failed to process audio"
   - JSON parsing errors → 500 status with "Failed to process audio"
   - Missing parameters → 500 status with "Failed to process audio"
   - Service exceptions → 500 status with "Failed to process audio: {exception_message}"
   - Service error responses → 200 status with error field populated

4. **Response Format**
   - Consistent TranscriptionResponse schema
   - Required fields: text, error, question_number
   - Proper type validation and serialization
   - Error responses maintain consistent structure 