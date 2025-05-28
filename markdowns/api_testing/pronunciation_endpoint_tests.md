# Pronunciation Endpoint API Test Implementation

## Files Referenced
- `tests/test_pronunciation_endpoint.py` - Complete test implementation
- `app/api/v1/endpoints/pronunciation_endpoint.py` - Pronunciation endpoint implementation
- `app/models/pronunciation_model.py` - Request/response models
- `app/services/pronunciation_service.py` - Pronunciation analysis service
- `app/core/config.py` - Configuration and dependencies

## Test Structure

### Test Class: `TestPronunciationEndpoint`
All tests are organized under a single test class with proper mocking setup.

### Mock Setup
```python
@pytest.fixture
def mock_pronunciation_service():
    """Mock PronunciationService.analyze_pronunciation for testing"""
    with patch('app.api.v1.endpoints.pronunciation_endpoint.PronunciationService.analyze_pronunciation') as mock:
        yield mock
```

## 1. Valid Pronunciation Analysis Tests

### `test_successful_pronunciation_assessment`
**Purpose:** Test successful pronunciation assessment with valid data

**Mock Setup:**
- Returns comprehensive pronunciation analysis results
- Includes all score types, error details, and improvement suggestions
- Uses realistic pronunciation data structure

**Test Data:**
```json
{
  "audio_file": "https://example.com/audio.mp3",
  "reference_text": "Hello world, this is a test",
  "question_number": 1
}
```

**Expected Response Structure:**
```json
{
  "status": "success",
  "audio_duration": 3.5,
  "transcript": "Hello world, this is a test",
  "overall_pronunciation_score": 85.0,
  "accuracy_score": 88.0,
  "fluency_score": 82.0,
  "prosody_score": 80.0,
  "completeness_score": 90.0,
  "critical_errors": [
    {
      "word": "world",
      "error_type": "mispronunciation",
      "expected": "wɜːrld",
      "actual": "wɔːrld"
    }
  ],
  "filler_words": [
    {
      "word": "um",
      "position": 2.1,
      "confidence": 0.95
    }
  ],
  "word_details": [
    {
      "word": "hello",
      "accuracy_score": 95.0,
      "error_type": "None"
    }
  ],
  "improvement_suggestion": "Focus on the pronunciation of 'world' - try to use the correct vowel sound."
}
```

**Assertions:**
- HTTP status code 200
- All pronunciation scores present and valid
- Critical errors and filler words arrays populated
- Word-level details included
- Service called with correct audio file and reference text
- Error field is None for successful requests

### `test_complex_reference_text_analysis`
**Purpose:** Test analysis with complex reference text containing multiple sentences

**Test Data:**
- Long reference text: "The quick brown fox jumps over the lazy dog. This sentence contains every letter of the alphabet."
- Multiple critical errors expected
- Detailed word-level analysis

**Assertions:**
- HTTP status code 200
- Multiple critical errors detected (2 errors)
- Empty filler words array (clean speech)
- Word details for multiple words (3 words)
- Question number preserved (2)

## 2. Error Handling from Service Tests

### `test_service_returns_error_status`
**Purpose:** Test graceful handling when service returns error status

**Mock Setup:**
- Service returns error status with partial data
- Error message: "Audio file format not supported"
- Partial transcript available

**Test Data:**
```json
{
  "audio_file": "https://example.com/unsupported.xyz",
  "reference_text": "Hello world",
  "question_number": 1
}
```

**Assertions:**
- HTTP status code 200 (endpoint handles error gracefully)
- Response status is "error"
- Error message preserved from service
- Partial transcript included
- All scores set to 0
- Empty arrays for errors, filler words, and word details
- Empty improvement suggestion

### `test_service_throws_exception`
**Purpose:** Test handling of service exceptions

**Mock Setup:**
- Service raises `Exception("Processing failed")`

**Assertions:**
- HTTP status code 500
- Error message: "Failed to assess pronunciation: Processing failed"

## 3. Request Validation Tests

### `test_missing_required_fields`
**Purpose:** Test validation error for missing required audio_file field

**Test Data:**
```json
{
  "reference_text": "Hello world"
  // Missing audio_file
}
```

**Assertions:**
- HTTP status code 422 (Pydantic validation error)
- Service function not called

### `test_optional_reference_text`
**Purpose:** Test request with missing reference_text (should use default None)

**Test Data:**
```json
{
  "audio_file": "https://example.com/audio.mp3",
  "question_number": 1
}
```

**Assertions:**
- HTTP status code 200 (reference_text is optional)
- Service called with None for reference_text
- Successful analysis without reference text

## 4. Response Format Validation Tests

### `test_complete_response_format_validation`
**Purpose:** Verify response follows `PronunciationResponse` schema exactly

**Assertions:**
- All required fields present:
  - `status`, `audio_duration`, `transcript`
  - `overall_pronunciation_score`, `accuracy_score`, `fluency_score`, `prosody_score`, `completeness_score`
  - `critical_errors`, `filler_words`, `word_details`
  - `improvement_suggestion`, `error`, `question_number`
- Correct field types validated:
  - Strings: status, transcript, improvement_suggestion
  - Numbers: all scores and audio_duration
  - Lists: critical_errors, filler_words, word_details
  - Optional: error (None for success)
  - Integer: question_number

## 5. Audio File Processing Tests

### `test_different_audio_formats`
**Purpose:** Test processing different audio file formats

**Test Setup:**
- Tests multiple audio formats: `.mp3`, `.wav`, `.webm`, `.m4a`
- Same mock response for all formats
- Iterates through format list

**Assertions:**
- All formats return HTTP 200
- Consistent "success" status for all formats
- Service called once for each format (4 total calls)

### `test_large_audio_file_processing`
**Purpose:** Test processing of large audio file (2 minutes duration)

**Mock Setup:**
- Audio duration: 120.0 seconds
- Long transcript with extended speech sample
- Multiple filler words with timestamps
- Stress-related pronunciation errors

**Assertions:**
- HTTP status code 200
- Audio duration correctly reported (120.0)
- Critical errors detected (1 stress error)
- Multiple filler words with positions (2 filler words)
- Service called once with large transcript

## 6. Pronunciation Scoring Validation Tests

### `test_score_range_validation`
**Purpose:** Test that all scores are within valid ranges (0-100)

**Mock Setup:**
- Various score scenarios with mid-range values
- All scores between 40-50 range

**Assertions:**
- HTTP status code 200
- All score fields within 0-100 range:
  - `overall_pronunciation_score`
  - `accuracy_score`
  - `fluency_score`
  - `prosody_score`
  - `completeness_score`

### `test_word_level_analysis`
**Purpose:** Test detailed word-level pronunciation analysis

**Mock Setup:**
- Reference text: "The quick brown fox"
- Word-level details for each word
- Mixed accuracy scores per word
- One critical error for "quick"

**Assertions:**
- HTTP status code 200
- Word details contains all words (4 words)
- Each word detail has required fields:
  - `word`, `accuracy_score`, `error_type`
- Word-level scores within 0-100 range
- Critical error corresponds to low-scoring word

## 7. Logging and Monitoring Tests

### `test_request_logging`
**Purpose:** Verify request processing is logged correctly

**Mock Setup:**
- Patches logger at endpoint level
- Returns valid analysis results

**Assertions:**
- HTTP status code 200
- Request logged with audio file URL:
  - `"Processing pronunciation assessment for: {audio_file}"`

### `test_error_logging`
**Purpose:** Verify errors are logged appropriately

**Mock Setup:**
- Service raises exception
- Logger patched to verify calls

**Assertions:**
- HTTP status code 500
- Exception logged with specific message:
  - `"Error assessing pronunciation: Test error"`

## 8. Performance and Edge Case Tests

### `test_concurrent_pronunciation_requests`
**Purpose:** Test multiple concurrent pronunciation assessment requests

**Test Setup:**
- Two different audio files and reference texts
- Different question numbers (1 and 2)
- Same mock response for both

**Assertions:**
- Both requests return HTTP 200
- Service called exactly twice
- No race conditions or conflicts

## Key Implementation Details

### Service Integration
The endpoint integrates with `PronunciationService.analyze_pronunciation()`:
```python
result = await PronunciationService.analyze_pronunciation(
    request.audio_file,
    request.reference_text
)
```

### Error Handling Pattern
The endpoint handles service errors gracefully:
- Service error status → HTTP 200 with error response
- Service exceptions → HTTP 500 with error details
- Validation errors → HTTP 422 with field details

### Response Mapping
The endpoint maps service results to standardized response format:
- Success responses include all pronunciation metrics
- Error responses zero out scores and clear arrays
- Question number always preserved from request

### Mock Data Structure
All mocks follow the expected service response format:
```python
{
    "status": "success",
    "audio_duration": float,
    "transcript": str,
    "overall_pronunciation_score": float,
    "accuracy_score": float,
    "fluency_score": float,
    "prosody_score": float,
    "completeness_score": float,
    "critical_errors": [{"word": str, "error_type": str, "expected": str, "actual": str}],
    "filler_words": [{"word": str, "position": float, "confidence": float}],
    "word_details": [{"word": str, "accuracy_score": float, "error_type": str}],
    "improvement_suggestion": str
}
```

### Test Coverage
- ✅ Successful pronunciation assessment scenarios
- ✅ Complex reference text processing
- ✅ Service error handling (error status and exceptions)
- ✅ Request validation (missing fields, optional fields)
- ✅ Response format validation
- ✅ Multiple audio format support
- ✅ Score range validation (0-100)
- ✅ Word-level analysis details
- ✅ Logging verification
- ✅ Large file processing
- ✅ Concurrent request handling

## Running the Tests
```bash
# Run all pronunciation endpoint tests
pytest tests/test_pronunciation_endpoint.py -v

# Run specific test
pytest tests/test_pronunciation_endpoint.py::TestPronunciationEndpoint::test_successful_pronunciation_assessment -v

# Run with coverage
pytest tests/test_pronunciation_endpoint.py --cov=app.api.v1.endpoints.pronunciation_endpoint

# Run specific test categories
pytest tests/test_pronunciation_endpoint.py -k "validation" -v
pytest tests/test_pronunciation_endpoint.py -k "error" -v
pytest tests/test_pronunciation_endpoint.py -k "score" -v
``` 