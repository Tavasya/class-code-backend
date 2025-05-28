# Fluency Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/fluency_endpoint.py` - Fluency endpoint implementation
- `app/models/fluency_model.py` - Request/response models
- `app/services/fluency_service.py` - Fluency analysis service
- `app/core/config.py` - Configuration and dependencies

## 1. Valid Fluency Analysis

### Scenario: Successful Fluency Assessment
**Preconditions:**
- Mock `analyze_fluency` service function
- Valid fluency request data
- Clean application state
- Mock successful analysis result

**User Actions:**
1. Send POST request to `/api/v1/fluency/analysis`
2. Include valid payload:
   ```json
   {
     "reference_text": "Hello world, this is a test of speech fluency",
     "word_details": [
       {"word": "hello", "accuracy_score": 85},
       {"word": "world", "accuracy_score": 90}
     ],
     "question_number": 1
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Response matches `FluencyResponse` schema
- `analyze_fluency` service function called with correct parameters
- Response contains fluency analysis results
- No HTTPException raised

### Scenario: Complex Word Details Analysis
**Preconditions:**
- Mock `analyze_fluency` service function
- Valid request with extensive word details
- Clean application state

**User Actions:**
1. Send POST request with complex word details:
   ```json
   {
     "reference_text": "The quick brown fox jumps over the lazy dog consistently",
     "word_details": [
       {"word": "the", "accuracy_score": 95},
       {"word": "quick", "accuracy_score": 80},
       {"word": "brown", "accuracy_score": 75},
       {"word": "fox", "accuracy_score": 90}
     ],
     "question_number": 2
   }
   ```

**Expected Assertions:**
- HTTP status code 200
- Service processes all word details correctly
- Fluency coherence analysis includes all words
- Response includes detailed fluency metrics

## 2. Service Error Handling

### Scenario: Service Returns Error Status
**Preconditions:**
- Mock `analyze_fluency` to return error response
- Valid request data
- Clean application state

**User Actions:**
1. Send valid fluency analysis request
2. Service returns error status:
   ```json
   {
     "status": "error",
     "error": "Insufficient data for fluency analysis"
   }
   ```

**Expected Assertions:**
- HTTP status code 500
- HTTPException raised with error detail
- Error message matches service error
- No successful response returned

### Scenario: Service Throws Exception
**Preconditions:**
- Mock `analyze_fluency` to raise exception
- Valid request data
- Clean application state

**User Actions:**
1. Send valid fluency analysis request
2. Service raises `Exception("Processing failed")`

**Expected Assertions:**
- HTTP status code 500
- HTTPException raised with exception message
- Error details contain exception string
- No partial response returned

## 3. Request Validation

### Scenario: Invalid Reference Text
**Preconditions:**
- Mock `analyze_fluency` service
- Clean application state

**User Actions:**
1. Send POST request with invalid reference text:
   ```json
   {
     "reference_text": "",
     "word_details": [],
     "question_number": 1
   }
   ```

**Expected Assertions:**
- HTTP status code 422 (Validation Error)
- Pydantic validation error response
- Service function not called
- Error details specify validation failures

### Scenario: Missing Required Fields
**Preconditions:**
- Mock `analyze_fluency` service
- Clean application state

**User Actions:**
1. Send POST request with missing fields:
   ```json
   {
     "reference_text": "Hello world"
   }
   ```

**Expected Assertions:**
- HTTP status code 422 (Validation Error)
- Validation errors for missing required fields
- Service function not called

### Scenario: Invalid Word Details Format
**Preconditions:**
- Mock `analyze_fluency` service
- Clean application state

**User Actions:**
1. Send POST request with malformed word details:
   ```json
   {
     "reference_text": "Hello world",
     "word_details": [
       {"invalid": "format"}
     ],
     "question_number": 1
   }
   ```

**Expected Assertions:**
- HTTP status code 422 (Validation Error)
- Validation error for word details structure
- Service function not called

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
- Response follows `FluencyResponse` schema exactly
- No null values where not expected
- Response serializes correctly to JSON

### Scenario: Service Response Validation
**Preconditions:**
- Mock service response with specific fluency metrics
- Valid request data
- Clean application state

**User Actions:**
1. Send valid request with service returning fluency data

**Expected Assertions:**
- Fluency scores within expected ranges
- Coherence analysis properly formatted
- Speech flow metrics included
- Response structure matches model definition

## 5. Fluency Analysis Components

### Scenario: Speech Flow Analysis
**Preconditions:**
- Mock `analyze_fluency` with speech flow data
- Valid word details with timing information
- Clean application state

**User Actions:**
1. Send request with detailed word timing data

**Expected Assertions:**
- Speech flow analysis processed correctly
- Timing information utilized properly
- Flow metrics calculated appropriately
- Response includes flow analysis results

### Scenario: Coherence Assessment
**Preconditions:**
- Mock `analyze_fluency` with coherence data
- Valid reference text for coherence analysis
- Clean application state

**User Actions:**
1. Send request with coherent reference text

**Expected Assertions:**
- Coherence analysis performed
- Text structure evaluated
- Logical flow assessed
- Coherence metrics included in response

## 6. Edge Cases

### Scenario: Empty Word Details Array
**Preconditions:**
- Mock `analyze_fluency` service
- Valid reference text but empty word details
- Clean application state

**User Actions:**
1. Send request with empty word details:
   ```json
   {
     "reference_text": "Hello world",
     "word_details": [],
     "question_number": 1
   }
   ```

**Expected Assertions:**
- Request processed (if validation allows)
- Service handles empty word details gracefully
- Response indicates limited analysis capability
- No service errors due to empty data

### Scenario: Single Word Analysis
**Preconditions:**
- Mock `analyze_fluency` service
- Single word reference text
- Clean application state

**User Actions:**
1. Send request with minimal data:
   ```json
   {
     "reference_text": "Hello",
     "word_details": [{"word": "hello", "accuracy_score": 85}],
     "question_number": 1
   }
   ```

**Expected Assertions:**
- Service processes minimal data appropriately
- Fluency analysis adapted for limited input
- Response indicates analysis limitations
- No errors due to insufficient data

## Integration Points to Verify

1. **Service Integration**
   - Proper service function calling
   - Parameter passing accuracy
   - Response handling and mapping
   - Error propagation working correctly

2. **Model Validation**
   - Request model validation enforced
   - Response model serialization working
   - Type conversion handled correctly
   - Required field enforcement

3. **Error Handling**
   - Service errors converted to HTTP exceptions
   - Validation errors properly formatted
   - Exception details preserved
   - Graceful error recovery 