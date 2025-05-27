# Transcription Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/transcription_endpoint.py` - Transcription endpoint implementation
- `app/models/transcription_model.py` - Request/response models
- `app/services/transcription_service.py` - Transcription processing service
- `app/core/config.py` - Configuration and dependencies

## 1. Direct Transcription Request

### Scenario: Valid Transcription Request
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Valid audio URL and parameters
- Clean application state
- Mock successful transcription result

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
- Response matches `TranscriptionResponse` schema
- `TranscriptionService.process_single_transcription` called with correct parameters
- Audio URL, question number, and submission URL passed correctly
- No base64 decoding attempted for direct request

### Scenario: Transcription Without Submission URL
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Valid audio URL without submission URL
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
- Service called with None for submission_url parameter
- Processing continues normally
- Response indicates successful transcription

## 2. Pub/Sub Message Processing

### Scenario: Valid Pub/Sub Transcription Message
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Valid base64 encoded Pub/Sub message
- Clean application state

**User Actions:**
1. Send POST request with Pub/Sub format:
   ```json
   {
     "message": {
       "data": "eyJhdWRpb191cmwiOiJodHRwczovL2V4YW1wbGUuY29tL3NwZWVjaC5tcDMiLCJxdWVzdGlvbl9udW1iZXIiOjEsInN1Ym1pc3Npb25fdXJsIjoidGVzdC1zdWJtaXNzaW9uIn0=",
       "messageId": "transcription-msg-123",
       "publishTime": "2024-01-01T00:00:00.000Z"
     }
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Base64 data decoded correctly
- JSON parsed from decoded data
- TranscriptionService called with decoded parameters
- Processing logged for question number

### Scenario: Invalid Base64 in Pub/Sub Message
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Malformed base64 data
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
- Base64 decoding error handled
- Error logged appropriately
- TranscriptionService not called

### Scenario: Invalid JSON in Pub/Sub Data
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Valid base64 but invalid JSON content
- Clean application state

**User Actions:**
1. Send POST request with base64 encoded invalid JSON:
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
- JSON parsing error handled
- Error logged with details
- TranscriptionService not called

## 3. Transcription Service Integration

### Scenario: Successful Transcription Processing
**Preconditions:**
- Mock TranscriptionService.process_single_transcription to return success
- Valid transcription request
- Clean application state

**User Actions:**
1. Send valid transcription request
2. Service returns successful transcription result

**Expected Assertions:**
- HTTP status code 200
- Response contains transcription success status
- TranscriptionService method called exactly once
- Response matches `TranscriptionResponse` schema
- Processing logged appropriately

### Scenario: Transcription Service Processing Failure
**Preconditions:**
- Mock TranscriptionService.process_single_transcription to raise exception
- Valid request data
- Clean application state

**User Actions:**
1. Send valid transcription request
2. Service raises `Exception("Transcription failed")`

**Expected Assertions:**
- HTTP status code 500
- HTTPException raised with error details: "Failed to process audio: Transcription failed"
- Error message contains service exception details
- Exception logged with full context
- No partial response returned

## 4. Request Format Detection

### Scenario: Pub/Sub vs Direct Request Detection
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Clean application state

**User Actions:**
1. Send direct request (no "message" field)
2. Send Pub/Sub request (with "message" field)

**Expected Assertions:**
- Direct request: No base64 decoding attempted
- Pub/Sub request: Base64 decoding performed
- Both requests result in same service call format
- Correct request type detected and handled
- Parameters extracted correctly in both cases

## 5. Parameter Validation

### Scenario: Missing Audio URL
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
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
- HTTP status code 500 (due to KeyError)
- Error handled in exception block
- TranscriptionService not called
- Error logged appropriately

### Scenario: Missing Question Number
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
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
- HTTP status code 500 (due to KeyError)
- Error handled in exception block
- TranscriptionService not called
- Error logged appropriately

## 6. Audio Processing for Transcription

### Scenario: Different Audio File Formats
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Various audio file URLs
- Clean application state

**User Actions:**
1. Test with different audio formats:
   - `.mp3` speech file
   - `.wav` speech file
   - `.webm` speech file
   - `.m4a` speech file

**Expected Assertions:**
- All formats processed by service
- Service called with correct URLs
- Format-specific handling delegated to service
- Consistent response structure

### Scenario: Poor Quality Audio
**Preconditions:**
- Mock TranscriptionService to handle poor quality audio
- Audio URL with background noise or unclear speech
- Clean application state

**User Actions:**
1. Send request with poor quality audio URL

**Expected Assertions:**
- Service attempts transcription
- Service handles quality issues appropriately
- Error handling delegated to service layer
- Appropriate response returned (may include partial transcription)

### Scenario: Silent or Empty Audio
**Preconditions:**
- Mock TranscriptionService to handle silent audio
- Audio URL with no speech content
- Clean application state

**User Actions:**
1. Send request with silent audio file

**Expected Assertions:**
- Service processes silent audio
- Service returns appropriate response for no speech
- No transcription errors due to silence
- Response indicates processing completion

## 7. Logging and Monitoring

### Scenario: Request Processing Logging
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Valid transcription request
- Logging configuration enabled

**User Actions:**
1. Send transcription request

**Expected Assertions:**
- Processing start logged with question number
- Audio URL transcription logged appropriately
- No sensitive data in logs
- Log levels appropriate for each message

### Scenario: Error Processing Logging
**Preconditions:**
- Mock TranscriptionService to raise exception
- Valid request triggering error
- Logging configuration enabled

**User Actions:**
1. Send request that triggers service exception

**Expected Assertions:**
- Error logged with full context using logger.exception
- Exception details included in logs
- Error level appropriate
- Stack trace available for debugging

## 8. Response Format Validation

### Scenario: Complete Transcription Response
**Preconditions:**
- Mock successful TranscriptionService response
- Valid transcription request
- Clean application state

**User Actions:**
1. Send valid request expecting complete response

**Expected Assertions:**
- Response follows `TranscriptionResponse` schema exactly
- All required fields present and valid types
- Transcription text properly formatted
- Response serializes correctly to JSON

### Scenario: Service Response Mapping
**Preconditions:**
- Mock TranscriptionService with specific response format
- Valid request data
- Clean application state

**User Actions:**
1. Send valid request with service returning transcription data

**Expected Assertions:**
- Service response mapped correctly to API response
- All transcription data preserved in response
- Response structure matches model definition
- Type conversion handled appropriately

## 9. Performance Considerations

### Scenario: Concurrent Transcription Processing
**Preconditions:**
- Mock TranscriptionService.process_single_transcription
- Multiple simultaneous requests
- Clean application state

**User Actions:**
1. Send multiple transcription requests simultaneously

**Expected Assertions:**
- All requests processed successfully
- No race conditions or conflicts
- TranscriptionService instances created properly
- Consistent response times

### Scenario: Long Audio File Processing
**Preconditions:**
- Mock TranscriptionService with processing delay
- Long duration audio file URL
- Clean application state

**User Actions:**
1. Send request with long audio file

**Expected Assertions:**
- Request processed within timeout limits
- Service handles long files appropriately
- Memory usage remains reasonable
- Response includes processing status

## 10. Speech Recognition Edge Cases

### Scenario: Multiple Languages
**Preconditions:**
- Mock TranscriptionService with language detection
- Audio with multiple languages
- Clean application state

**User Actions:**
1. Send request with multilingual audio

**Expected Assertions:**
- Service handles language detection
- Transcription attempts all detected languages
- Response includes language information if available
- Processing continues despite language complexity

### Scenario: Technical or Domain-Specific Speech
**Preconditions:**
- Mock TranscriptionService with technical vocabulary
- Audio containing specialized terminology
- Clean application state

**User Actions:**
1. Send request with technical speech content

**Expected Assertions:**
- Service processes specialized vocabulary
- Transcription quality maintained for technical terms
- Response includes technical content appropriately
- No errors due to vocabulary complexity

## Integration Points to Verify

1. **Request Processing Flow**
   - Raw request → Format detection → Data extraction → Service call
   - Error handling at each processing stage
   - Consistent response format regardless of input format

2. **TranscriptionService Integration**
   - Proper service instantiation
   - Parameter passing accuracy
   - Response handling and mapping
   - Error propagation working correctly

3. **Speech Processing Pipeline**
   - Audio format handling
   - Speech recognition accuracy
   - Transcription quality validation
   - Performance optimization for various audio types 