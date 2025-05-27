# Grammar Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/grammar_endpoint.py` - Grammar endpoint implementation
- `app/models/grammer_model.py` - Request/response models (note: typo in filename)
- `app/services/grammar_service.py` - Grammar analysis service
- `app/core/config.py` - Configuration and dependencies

## 1. Valid Grammar Analysis

### Scenario: Successful Grammar Analysis
**Preconditions:**
- Mock `analyze_grammar` service function
- Valid transcript with sufficient length
- Clean application state
- Mock successful analysis result

**User Actions:**
1. Send POST request to `/api/v1/grammar/analysis`
2. Include valid payload:
   ```json
   {
     "transcript": "This is a good sentence with proper grammar and vocabulary usage."
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Response matches `GrammarResponse` schema
- `analyze_grammar` service function called with correct transcript
- Response contains:
  - `status`: "success"
  - `grammar_corrections`: array of corrections
  - `vocabulary_suggestions`: array of suggestions
- Logging indicates analysis completion with statistics

### Scenario: Complex Transcript Analysis
**Preconditions:**
- Mock `analyze_grammar` service function
- Valid complex transcript
- Clean application state

**User Actions:**
1. Send POST request with complex transcript:
   ```json
   {
     "transcript": "The student was learning English language very quickly and they demonstrate good understanding of grammatical rules. However, there is still room for improvement in vocabulary choices and sentence structure."
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Service processes complex transcript correctly
- Grammar corrections include sentence-level issues
- Vocabulary suggestions provide appropriate alternatives
- Response statistics logged correctly

## 2. Input Validation

### Scenario: Transcript Too Short
**Preconditions:**
- Mock `analyze_grammar` service function
- Clean application state

**User Actions:**
1. Send POST request with short transcript:
   ```json
   {
     "transcript": "Short"
   }
   ```

**Expected Assertions:**
- HTTP status code 400
- HTTPException with detail: "Transcript is too short for analysis (minimum 10 characters)"
- Service function not called
- Error logged appropriately

### Scenario: Empty Transcript
**Preconditions:**
- Mock `analyze_grammar` service function
- Clean application state

**User Actions:**
1. Send POST request with empty transcript:
   ```json
   {
     "transcript": ""
   }
   ```

**Expected Assertions:**
- HTTP status code 400
- HTTPException indicating transcript too short
- Service function not called
- No processing attempted

### Scenario: Whitespace-Only Transcript
**Preconditions:**
- Mock `analyze_grammar` service function
- Clean application state

**User Actions:**
1. Send POST request with whitespace transcript:
   ```json
   {
     "transcript": "   \n\t   "
   }
   ```

**Expected Assertions:**
- HTTP status code 400
- HTTPException for insufficient content after stripping
- Service function not called
- Whitespace handling working correctly

## 3. Service Integration

### Scenario: Service Returns Grammar Corrections
**Preconditions:**
- Mock `analyze_grammar` to return corrections
- Valid transcript
- Clean application state

**User Actions:**
1. Send valid grammar analysis request
2. Service returns:
   ```json
   {
     "grammar_corrections": [
       {"error": "subject-verb disagreement", "suggestion": "was -> were"},
       {"error": "missing article", "suggestion": "add 'the' before 'student'"}
     ],
     "vocabulary_suggestions": [
       {"word": "good", "suggestion": "excellent", "context": "quality"}
     ]
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Response contains all corrections and suggestions
- Statistics logged correctly (2 grammar issues, 1 vocabulary suggestion)
- Response structure matches expected format

### Scenario: Service Throws Exception
**Preconditions:**
- Mock `analyze_grammar` to raise exception
- Valid transcript
- Clean application state

**User Actions:**
1. Send valid grammar analysis request
2. Service raises `Exception("Analysis service unavailable")`

**Expected Assertions:**
- HTTP status code 500
- HTTPException with detail: "Error analyzing grammar: Analysis service unavailable"
- Exception logged with full context
- No partial response returned

## 4. Response Format Validation

### Scenario: Complete Grammar Response
**Preconditions:**
- Mock successful service response with full data
- Valid transcript
- Clean application state

**User Actions:**
1. Send valid request expecting complete response

**Expected Assertions:**
- Response follows `GrammarResponse` schema exactly
- All required fields present and valid types
- Arrays properly formatted
- No null values where not expected
- Response serializes correctly to JSON

### Scenario: Empty Corrections Response
**Preconditions:**
- Mock service returning no corrections
- Valid transcript with perfect grammar
- Clean application state

**User Actions:**
1. Send request with grammatically correct transcript

**Expected Assertions:**
- HTTP status code 200
- Response contains empty arrays for corrections and suggestions
- Statistics logged showing 0 issues found
- Success status maintained

## 5. Logging and Monitoring

### Scenario: Request Logging
**Preconditions:**
- Mock `analyze_grammar` service
- Valid transcript
- Logging configuration enabled

**User Actions:**
1. Send grammar analysis request

**Expected Assertions:**
- Request logged with transcript length
- Processing completion logged with statistics
- Log levels appropriate for each message
- No sensitive data logged

### Scenario: Error Logging
**Preconditions:**
- Mock service to raise exception
- Valid transcript
- Logging configuration enabled

**User Actions:**
1. Send request that triggers service exception

**Expected Assertions:**
- Exception logged with full context
- Error logged at appropriate level
- No data corruption in logs
- Stack trace included for debugging

## 6. Error Handling

### Scenario: Malformed Request Body
**Preconditions:**
- Mock `analyze_grammar` service
- Clean application state

**User Actions:**
1. Send POST request with missing transcript field:
   ```json
   {
     "invalid_field": "some text"
   }
   ```

**Expected Assertions:**
- HTTP status code 422 (Validation Error)
- Pydantic validation error response
- Service function not called
- Error details specify missing required field

### Scenario: Invalid JSON
**Preconditions:**
- Mock `analyze_grammar` service
- Clean application state

**User Actions:**
1. Send POST request with malformed JSON

**Expected Assertions:**
- HTTP status code 400 or 422
- JSON parsing error handled gracefully
- Service function not called
- Appropriate error response returned

## 7. Performance Considerations

### Scenario: Large Transcript Processing
**Preconditions:**
- Mock `analyze_grammar` service with processing delay
- Very large transcript (>1000 characters)
- Clean application state

**User Actions:**
1. Send request with large transcript

**Expected Assertions:**
- Request processed within reasonable time limits
- Service handles large input appropriately
- Memory usage remains reasonable
- Response includes processing time in logs

### Scenario: Concurrent Analysis Requests
**Preconditions:**
- Mock `analyze_grammar` service
- Multiple valid transcripts
- Clean application state

**User Actions:**
1. Send multiple grammar analysis requests simultaneously

**Expected Assertions:**
- All requests processed successfully
- No race conditions or conflicts
- Consistent response quality
- Proper request isolation

## Integration Points to Verify

1. **Service Integration**
   - Proper service function calling
   - Parameter passing accuracy (transcript)
   - Response handling and mapping
   - Error propagation working correctly

2. **Model Validation**
   - Request model validation enforced
   - Response model serialization working
   - Type conversion handled correctly
   - Required field enforcement

3. **Logging Integration**
   - Request processing logged
   - Error cases logged appropriately
   - Statistics captured and logged
   - Performance metrics tracked 