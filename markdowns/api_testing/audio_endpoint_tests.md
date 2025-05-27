# Audio Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/audio_endpoint.py` - Audio endpoint implementation
- `app/models/audio_model.py` - Request/response models
- `app/services/audio_service.py` - Audio processing service
- `app/core/config.py` - Configuration and dependencies

## 1. Direct Audio Processing Request

### Scenario: Valid Audio Conversion Request
**Preconditions:**
- Mock AudioService.process_single_audio
- Valid audio URL and parameters
- Clean application state
- Mock successful conversion result

**User Actions:**
1. Send POST request to `/api/v1/audio/audio_proccessing`
2. Include valid payload:
   ```json
   {
     "audio_url": "https://example.com/audio.mp3",
     "question_number": 1,
     "submission_url": "test-submission-123"
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Response matches `AudioConvertResponse` schema
- `AudioService.process_single_audio` called with correct parameters
- Audio URL, question number, and submission URL passed correctly
- No base64 decoding attempted for direct request

### Scenario: Audio Conversion Without Submission URL
**Preconditions:**
- Mock AudioService.process_single_audio
- Valid audio URL without submission URL
- Clean application state

**User Actions:**
1. Send POST request without submission_url:
   ```json
   {
     "audio_url": "https://example.com/audio.wav",
     "question_number": 2
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Service called with None for submission_url parameter
- Processing continues normally
- Response indicates successful conversion

## 2. Pub/Sub Message Processing

### Scenario: Valid Pub/Sub Audio Message
**Preconditions:**
- Mock AudioService.process_single_audio
- Valid base64 encoded Pub/Sub message
- Clean application state

**User Actions:**
1. Send POST request with Pub/Sub format:
   ```json
   {
     "message": {
       "data": "eyJhdWRpb191cmwiOiJodHRwczovL2V4YW1wbGUuY29tL2F1ZGlvLm1wMyIsInF1ZXN0aW9uX251bWJlciI6MSwic3VibWlzc2lvbl91cmwiOiJ0ZXN0LXN1Ym1pc3Npb24ifQ==",
       "messageId": "audio-msg-123",
       "publishTime": "2024-01-01T00:00:00.000Z"
     }
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Base64 data decoded correctly
- JSON parsed from decoded data
- AudioService called with decoded parameters
- Processing logged for question number

### Scenario: Invalid Base64 in Pub/Sub Message
**Preconditions:**
- Mock AudioService.process_single_audio
- Malformed base64 data
- Clean application state

**User Actions:**
1. Send POST request with invalid base64:
   ```json
   {
     "message": {
       "data": "invalid-base64-data!@#$",
       "messageId": "audio-msg-456"
     }
   }
   ```

**Expected Assertions:**
- HTTP status code 500
- Base64 decoding error handled
- Error logged appropriately
- AudioService not called

### Scenario: Invalid JSON in Pub/Sub Data
**Preconditions:**
- Mock AudioService.process_single_audio
- Valid base64 but invalid JSON content
- Clean application state

**User Actions:**
1. Send POST request with base64 encoded invalid JSON:
   ```json
   {
     "message": {
       "data": "aW52YWxpZC1qc29uLWNvbnRlbnQ=",
       "messageId": "audio-msg-789"
     }
   }
   ```

**Expected Assertions:**
- HTTP status code 500
- JSON parsing error handled
- Error logged with details
- AudioService not called

## 3. Audio Service Integration

### Scenario: Successful Audio Processing
**Preconditions:**
- Mock AudioService.process_single_audio to return success
- Valid audio processing request
- Clean application state

**User Actions:**
1. Send valid audio processing request
2. Service returns successful conversion result

**Expected Assertions:**
- HTTP status code 200
- Response contains conversion success status
- AudioService method called exactly once
- Response matches `AudioConvertResponse` schema
- Processing logged appropriately

### Scenario: Audio Service Processing Failure
**Preconditions:**
- Mock AudioService.process_single_audio to raise exception
- Valid request data
- Clean application state

**User Actions:**
1. Send valid audio processing request
2. Service raises `Exception("Audio conversion failed")`

**Expected Assertions:**
- HTTP status code 500
- HTTPException raised with error details
- Error message contains service exception details
- Error logged appropriately
- No partial response returned

## 4. Request Format Detection

### Scenario: Pub/Sub vs Direct Request Detection
**Preconditions:**
- Mock AudioService.process_single_audio
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
- Mock AudioService.process_single_audio
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
- AudioService not called
- Error logged appropriately

### Scenario: Missing Question Number
**Preconditions:**
- Mock AudioService.process_single_audio
- Clean application state

**User Actions:**
1. Send POST request without question_number:
   ```json
   {
     "audio_url": "https://example.com/audio.mp3",
     "submission_url": "test"
   }
   ```

**Expected Assertions:**
- HTTP status code 500 (due to KeyError)
- Error handled in exception block
- AudioService not called
- Error logged appropriately

## 6. Audio URL Processing

### Scenario: Different Audio File Formats
**Preconditions:**
- Mock AudioService.process_single_audio
- Various audio file URLs
- Clean application state

**User Actions:**
1. Test with different audio formats:
   - `.mp3` file
   - `.wav` file
   - `.webm` file
   - `.m4a` file

**Expected Assertions:**
- All formats processed by service
- Service called with correct URLs
- Format-specific handling delegated to service
- Consistent response structure

### Scenario: Invalid Audio URL
**Preconditions:**
- Mock AudioService.process_single_audio to handle invalid URLs
- Invalid or malformed URL
- Clean application state

**User Actions:**
1. Send request with invalid audio URL:
   ```json
   {
     "audio_url": "not-a-valid-url",
     "question_number": 1
   }
   ```

**Expected Assertions:**
- Service called with invalid URL
- Service handles URL validation
- Error handling delegated to service layer
- Appropriate error response returned

## 7. Logging and Monitoring

### Scenario: Request Processing Logging
**Preconditions:**
- Mock AudioService.process_single_audio
- Valid audio processing request
- Logging configuration enabled

**User Actions:**
1. Send audio processing request

**Expected Assertions:**
- Processing start logged with question number
- Audio URL conversion logged appropriately
- No sensitive data in logs
- Log levels appropriate for each message

### Scenario: Error Processing Logging
**Preconditions:**
- Mock AudioService to raise exception
- Valid request triggering error
- Logging configuration enabled

**User Actions:**
1. Send request that triggers service exception

**Expected Assertions:**
- Error logged with full context
- Exception details included in logs
- Error level appropriate
- Stack trace available for debugging

## 8. Response Format Validation

### Scenario: Complete Audio Response
**Preconditions:**
- Mock successful AudioService response
- Valid audio processing request
- Clean application state

**User Actions:**
1. Send valid request expecting complete response

**Expected Assertions:**
- Response follows `AudioConvertResponse` schema exactly
- All required fields present and valid types
- No null values where not expected
- Response serializes correctly to JSON

### Scenario: Service Response Mapping
**Preconditions:**
- Mock AudioService with specific response format
- Valid request data
- Clean application state

**User Actions:**
1. Send valid request with service returning audio data

**Expected Assertions:**
- Service response mapped correctly to API response
- All service data preserved in response
- Response structure matches model definition
- Type conversion handled appropriately

## 9. Performance Considerations

### Scenario: Concurrent Audio Processing
**Preconditions:**
- Mock AudioService.process_single_audio
- Multiple simultaneous requests
- Clean application state

**User Actions:**
1. Send multiple audio processing requests simultaneously

**Expected Assertions:**
- All requests processed successfully
- No race conditions or conflicts
- AudioService instances created properly
- Consistent response times

### Scenario: Large Audio File Processing
**Preconditions:**
- Mock AudioService with processing delay
- Large audio file URL
- Clean application state

**User Actions:**
1. Send request with large audio file

**Expected Assertions:**
- Request processed within timeout limits
- Service handles large files appropriately
- Memory usage remains reasonable
- Response includes processing status

## Integration Points to Verify

1. **Request Processing Flow**
   - Raw request → Format detection → Data extraction → Service call
   - Error handling at each processing stage
   - Consistent response format regardless of input format

2. **AudioService Integration**
   - Proper service instantiation
   - Parameter passing accuracy
   - Response handling and mapping
   - Error propagation working correctly

3. **Message Format Handling**
   - Pub/Sub message decoding
   - Direct request processing
   - Parameter extraction consistency
   - Error handling for malformed data 