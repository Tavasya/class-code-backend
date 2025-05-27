# Pronunciation Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/pronunciation_endpoint.py` - Pronunciation endpoint implementation
- `app/models/pronunciation_model.py` - Request/response models
- `app/services/pronunciation_service.py` - Pronunciation analysis service
- `app/core/config.py` - Configuration and dependencies

## 1. Valid Pronunciation Analysis

### Scenario: Successful Pronunciation Assessment
**Preconditions:**
- Mock PronunciationService.analyze_pronunciation
- Valid audio file and reference text
- Clean application state
- Mock successful analysis result

**User Actions:**
1. Send POST request to `/api/v1/pronunciation/analysis`
2. Include valid payload:
   ```json
   {
     "audio_file": "https://example.com/audio.mp3",
     "reference_text": "Hello world, this is a test",
     "question_number": 1
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Response matches `PronunciationResponse` schema
- `PronunciationService.analyze_pronunciation` called with correct parameters
- Response contains all required fields:
  - `status`: "success"
  - `audio_duration`: positive number
  - `transcript`: string
  - `overall_pronunciation_score`: 0-100
  - `accuracy_score`: 0-100
  - `fluency_score`: 0-100
  - `prosody_score`: 0-100
  - `completeness_score`: 0-100
  - `word_details`: array
  - `question_number`: matches request

### Scenario: Complex Reference Text Analysis
**Preconditions:**
- Mock PronunciationService
- Valid audio file with complex reference text
- Clean application state

**User Actions:**
1. Send POST request with complex text:
   ```json
   {
     "audio_file": "https://example.com/complex-audio.mp3",
     "reference_text": "The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet.",
     "question_number": 2
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Service processes complex text correctly
- Word-level analysis includes all words
- Detailed pronunciation feedback provided

## 2. Error Handling from Service

### Scenario: Service Returns Error Status
**Preconditions:**
- Mock PronunciationService to return error result
- Valid request data
- Clean application state

**User Actions:**
1. Send valid pronunciation analysis request
2. Service returns error status:
   ```json
   {
     "status": "error",
     "error": "Audio file format not supported",
     "transcript": "partial transcript"
   }
   ```

**Expected Assertions:**
- HTTP status code 200 (endpoint handles error gracefully)
- Response contains:
  - `status`: "error"
  - `error`: error message from service
  - `transcript`: partial transcript if available
  - All score fields set to 0
  - Empty arrays for details
  - `question_number`: matches request

### Scenario: Service Throws Exception
**Preconditions:**
- Mock PronunciationService to raise exception
- Valid request data
- Clean application state

**User Actions:**
1. Send valid pronunciation analysis request
2. Service raises `Exception("Processing failed")`

**Expected Assertions:**
- HTTP status code 500
- HTTPException raised with appropriate detail
- Error message contains service exception details
- No partial response returned

## 3. Request Validation

### Scenario: Invalid Audio File URL
**Preconditions:**
- Mock PronunciationService
- Clean application state

**User Actions:**
1. Send POST request with invalid audio URL:
   ```json
   {
     "audio_file": "not-a-valid-url",
     "reference_text": "Hello world",
     "question_number": 1
   }
   ```

**Expected Assertions:**
- HTTP status code 422 (Validation Error)
- Pydantic validation error response
- Service method not called
- Error details specify URL validation failure

### Scenario: Missing Required Fields
**Preconditions:**
- Mock PronunciationService
- Clean application state

**User Actions:**
1. Send POST request with missing fields:
   ```json
   {
     "audio_file": "https://example.com/audio.mp3"
   }
   ```

**Expected Assertions:**
- HTTP status code 422 (Validation Error)
- Validation errors for missing required fields
- Service method not called

### Scenario: Invalid Question Number
**Preconditions:**
- Mock PronunciationService
- Clean application state

**User Actions:**
1. Send POST request with invalid question number:
   ```json
   {
     "audio_file": "https://example.com/audio.mp3",
     "reference_text": "Hello world",
     "question_number": -1
   }
   ```

**Expected Assertions:**
- HTTP status code 422 (Validation Error)
- Validation error for invalid question number
- Service method not called

## 4. Response Format Validation

### Scenario: Complete Successful Response
**Preconditions:**
- Mock successful service response with all fields
- Valid request data
- Clean application state

**User Actions:**
1. Send valid request expecting complete response

**Expected Assertions:**
- All response fields present and valid types
- Scores within valid ranges (0-100)
- Arrays properly formatted
- No null values where not expected
- Response serializes correctly to JSON

### Scenario: Partial Response Handling
**Preconditions:**
- Mock service response missing optional fields
- Valid request data
- Clean application state

**User Actions:**
1. Send valid request with service returning minimal data

**Expected Assertions:**
- Required fields always present
- Optional fields handled gracefully
- Default values used where appropriate
- Response remains valid

## 5. Audio File Processing

### Scenario: Different Audio Formats
**Preconditions:**
- Mock PronunciationService for different formats
- Clean application state

**User Actions:**
1. Test with various audio file formats:
   - `.mp3` file
   - `.wav` file  
   - `.webm` file
   - `.m4a` file

**Expected Assertions:**
- All supported formats processed correctly
- Service called with correct file URLs
- Format-specific handling working
- Consistent response structure

### Scenario: Large Audio File
**Preconditions:**
- Mock PronunciationService with large file processing
- Clean application state

**User Actions:**
1. Send request with large audio file URL

**Expected Assertions:**
- Request processed without timeout
- Service handles large files appropriately
- Memory usage remains reasonable
- Response includes processing time info

## 6. Pronunciation Scoring Validation

### Scenario: Score Range Validation
**Preconditions:**
- Mock service with various score scenarios
- Clean application state

**User Actions:**
1. Test with different pronunciation quality levels

**Expected Assertions:**
- All scores between 0-100
- Scores correlate with pronunciation quality
- Individual component scores logical
- Overall score calculated correctly

### Scenario: Word-Level Analysis
**Preconditions:**
- Mock detailed word analysis
- Valid multi-word reference text
- Clean application state

**User Actions:**
1. Send request with multi-word reference text

**Expected Assertions:**
- `word_details` array contains all words
- Each word has pronunciation metrics
- Word-level scores consistent with overall
- Detailed feedback provided per word

## Integration Points to Verify

1. **Service Integration**
   - Proper dependency injection
   - Service method parameters passed correctly
   - Service response mapped to API response
   - Error propagation working

2. **Model Validation**
   - Request model validation enforced
   - Response model serialization working
   - Type conversion handled correctly
   - Required field enforcement

3. **Logging Integration**
   - Processing requests logged
   - Error cases logged appropriately
   - Service calls tracked
   - Performance metrics captured 