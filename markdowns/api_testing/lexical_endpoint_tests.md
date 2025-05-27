# Lexical Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/lexical_endpoint.py` - Lexical endpoint implementation
- `app/models/lexical_model.py` - Request/response models
- `app/services/lexical_service.py` - Lexical analysis service
- `app/core/config.py` - Configuration and dependencies

## 1. Valid Lexical Analysis

### Scenario: Successful Lexical Analysis
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Valid text input with multiple sentences
- Clean application state
- Mock successful analysis result

**User Actions:**
1. Send POST request to `/api/v1/lexical/analyze`
2. Include valid text parameter:
   ```
   text="This is a comprehensive sentence. It demonstrates vocabulary usage. The analysis should provide feedback."
   ```

**Expected Assertions:**
- HTTP status code 200
- Response matches `LexicalAnalysisResponse` schema
- `analyze_lexical_resources` called with sentence array
- Text properly split into sentences
- Response contains `lexical_feedback` array
- No error field in response

### Scenario: Complex Multi-Sentence Text
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Valid complex text input
- Clean application state

**User Actions:**
1. Send POST request with complex text:
   ```
   text="The student demonstrated exceptional vocabulary knowledge. However, there were some areas for improvement. Sophisticated word choices were evident throughout the response. Academic language usage was particularly strong."
   ```

**Expected Assertions:**
- HTTP status code 200
- Text split into 4 sentences correctly
- All sentences passed to service function
- Lexical feedback provided for each sentence
- Response structure maintained

## 2. Input Processing and Validation

### Scenario: Empty Text Input
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Clean application state

**User Actions:**
1. Send POST request with empty text:
   ```
   text=""
   ```

**Expected Assertions:**
- HTTP status code 200
- Response contains:
  - `lexical_feedback`: empty array
  - `error`: "No valid sentences found in the input text"
- Service function not called
- Graceful handling of empty input

### Scenario: Text Without Sentences
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Clean application state

**User Actions:**
1. Send POST request with text without periods:
   ```
   text="just some words without proper sentence structure"
   ```

**Expected Assertions:**
- HTTP status code 200
- Response indicates no valid sentences found
- Error message provided appropriately
- No service processing attempted

### Scenario: Text With Only Periods
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Clean application state

**User Actions:**
1. Send POST request with just punctuation:
   ```
   text="... ... ."
   ```

**Expected Assertions:**
- HTTP status code 200
- Empty sentences array after filtering
- Error response for no valid sentences
- Proper handling of edge case

## 3. Sentence Processing

### Scenario: Single Sentence Analysis
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Valid single sentence input
- Clean application state

**User Actions:**
1. Send POST request with single sentence:
   ```
   text="This is a well-constructed sentence with appropriate vocabulary."
   ```

**Expected Assertions:**
- HTTP status code 200
- Single sentence properly extracted
- Service called with one-element array
- Lexical feedback provided for single sentence
- Response structure maintained

### Scenario: Sentences with Various Punctuation
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Text with different sentence endings
- Clean application state

**User Actions:**
1. Send POST request with mixed punctuation:
   ```
   text="This is a statement. Is this a question? This is exciting! Another statement."
   ```

**Expected Assertions:**
- HTTP status code 200
- Only sentences ending with periods processed
- Questions and exclamations filtered out (based on current split logic)
- Service receives appropriate sentence array
- Consistent processing behavior

## 4. Service Integration

### Scenario: Service Returns Lexical Feedback
**Preconditions:**
- Mock `analyze_lexical_resources` to return feedback
- Valid text input
- Clean application state

**User Actions:**
1. Send valid lexical analysis request
2. Service returns:
   ```json
   [
     {
       "sentence": "This is a comprehensive sentence",
       "vocabulary_level": "intermediate",
       "suggestions": ["consider using 'thorough' instead of 'comprehensive'"]
     }
   ]
   ```

**Expected Assertions:**
- HTTP status code 200
- Response contains all feedback from service
- Feedback structure preserved in response
- No errors in response

### Scenario: Service Throws Exception
**Preconditions:**
- Mock `analyze_lexical_resources` to raise exception
- Valid text input
- Clean application state

**User Actions:**
1. Send valid lexical analysis request
2. Service raises `Exception("Lexical service unavailable")`

**Expected Assertions:**
- HTTP status code 500
- HTTPException with detail: "Error analyzing lexical resources: Lexical service unavailable"
- Exception propagated correctly
- No partial response returned

## 5. Response Format Validation

### Scenario: Complete Lexical Response
**Preconditions:**
- Mock successful service response with feedback
- Valid text input
- Clean application state

**User Actions:**
1. Send valid request expecting complete response

**Expected Assertions:**
- Response follows `LexicalAnalysisResponse` schema exactly
- `lexical_feedback` field present and properly formatted
- No `error` field when successful
- Response serializes correctly to JSON

### Scenario: Error Response Format
**Preconditions:**
- Mock scenario triggering error response
- Invalid or empty text input
- Clean application state

**User Actions:**
1. Send request that triggers error condition

**Expected Assertions:**
- Response contains `error` field with descriptive message
- `lexical_feedback` field present (empty array)
- Response structure consistent
- HTTP status still 200 for handled errors

## 6. Text Processing Edge Cases

### Scenario: Text with Whitespace and Special Characters
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Text with various whitespace and characters
- Clean application state

**User Actions:**
1. Send POST request with complex text:
   ```
   text="  This sentence has extra spaces.   \n\nThis has newlines.\t\tThis has tabs.  "
   ```

**Expected Assertions:**
- HTTP status code 200
- Sentences properly extracted and trimmed
- Whitespace handling working correctly
- Clean sentences passed to service

### Scenario: Very Long Text Input
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Very long text with many sentences
- Clean application state

**User Actions:**
1. Send POST request with lengthy text (>1000 characters)

**Expected Assertions:**
- HTTP status code 200
- All sentences properly extracted
- Service handles large sentence arrays
- Response processed within reasonable time

## 7. Error Handling

### Scenario: Missing Text Parameter
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Clean application state

**User Actions:**
1. Send POST request without text parameter

**Expected Assertions:**
- HTTP status code 422 (Validation Error)
- FastAPI validation error response
- Service function not called
- Error details specify missing parameter

### Scenario: Invalid Request Format
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Clean application state

**User Actions:**
1. Send POST request with wrong content type or malformed data

**Expected Assertions:**
- Appropriate HTTP error status
- Request parsing error handled
- Service function not called
- Error response returned

## 8. Performance Considerations

### Scenario: Concurrent Lexical Analysis
**Preconditions:**
- Mock `analyze_lexical_resources` service function
- Multiple text inputs
- Clean application state

**User Actions:**
1. Send multiple lexical analysis requests simultaneously

**Expected Assertions:**
- All requests processed successfully
- No race conditions or conflicts
- Consistent response quality
- Proper request isolation

### Scenario: Large Text Processing
**Preconditions:**
- Mock `analyze_lexical_resources` with processing delay
- Large text input with many sentences
- Clean application state

**User Actions:**
1. Send request with large text input

**Expected Assertions:**
- Request processed within reasonable time
- Memory usage remains appropriate
- Service handles large input correctly
- Response quality maintained

## Integration Points to Verify

1. **Service Integration**
   - Proper service function calling
   - Sentence array parameter passing
   - Response handling and mapping
   - Error propagation working correctly

2. **Text Processing**
   - Sentence splitting logic working
   - Whitespace handling appropriate
   - Special character processing
   - Input validation and filtering

3. **Response Model Integration**
   - Response model serialization working
   - Type conversion handled correctly
   - Error response format consistent
   - Schema compliance maintained 