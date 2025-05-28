# Results Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/results_endpoint.py` - Results endpoint implementation
- `app/core/results_store.py` - Results storage and retrieval system
- `app/models/schemas.py` - Response models for results
- `app/core/config.py` - Configuration and dependencies

## 1. Get Submission Results (Transformed)

### Scenario: Valid Submission Results Retrieval
**Preconditions:**
- Mock `results_store.get_result_transformed` to return data
- Valid submission URL exists in store
- Clean application state
- Mock standardized result format

**User Actions:**
1. Send GET request to `/api/v1/results/submission/test-submission-123`

**Expected Assertions:**
- HTTP status code 200
- Response contains list of transformed results
- `results_store.get_result_transformed` called with correct submission_url
- Response follows standardized format (List[Dict[str, Any]])
- Data properly serialized as JSON
- Each item in response is a dictionary
- Response length matches expected data

### Scenario: Non-Existent Submission
**Preconditions:**
- Mock `results_store.get_result_transformed` to return None
- Submission URL does not exist in store
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/results/submission/non-existent-submission`

**Expected Assertions:**
- HTTP status code 404
- HTTPException with detail: "No results found for submission: non-existent-submission"
- Store method called with correct parameter
- No results returned

### Scenario: Complex Submission Results
**Preconditions:**
- Mock `results_store.get_result_transformed` with complex data
- Multiple analysis results for submission
- Clean application state

**User Actions:**
1. Send GET request for submission with multiple question results

**Expected Assertions:**
- HTTP status code 200
- All question results included in response
- Transformed format maintained across all results
- Response structure consistent
- Complete analysis data preserved
- Different analysis types preserved (pronunciation, grammar, fluency)
- Complex nested data structures maintained
- Question numbers correctly included

### Scenario: Empty Results List
**Preconditions:**
- Mock `results_store.get_result_transformed` to return empty list
- Valid submission with no results
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/results/submission/empty-submission`

**Expected Assertions:**
- HTTP status code 200
- Response is empty list
- Response type is list
- No errors thrown for empty results

## 2. Get Raw Submission Results

### Scenario: Valid Raw Results Retrieval
**Preconditions:**
- Mock `results_store.get_result` to return raw data
- Valid submission URL exists in store
- Clean application state
- Mock raw result format

**User Actions:**
1. Send GET request to `/api/v1/results/submission/test-submission-123/raw`

**Expected Assertions:**
- HTTP status code 200
- Response contains raw analysis results
- `results_store.get_result` called with correct submission_url
- Raw format preserved (debugging format)
- All original data included
- Response type is dictionary
- Nested structures preserved exactly

### Scenario: Non-Existent Submission Raw Results
**Preconditions:**
- Mock `results_store.get_result` to return None
- Submission URL does not exist in store
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/results/submission/non-existent-submission/raw`

**Expected Assertions:**
- HTTP status code 404
- HTTPException with detail: "No results found for submission: non-existent-submission"
- Store method called with correct parameter
- No results returned

### Scenario: Empty Dict Raw Results
**Preconditions:**
- Mock `results_store.get_result` to return empty dict
- Submission URL exists but has no data
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/results/submission/empty-submission/raw`

**Expected Assertions:**
- HTTP status code 404
- HTTPException with detail: "No results found for submission: empty-submission"
- Empty dict treated as no results

### Scenario: Raw Results Format Validation
**Preconditions:**
- Mock `results_store.get_result` with raw format data
- Valid submission with unprocessed results
- Clean application state

**User Actions:**
1. Send GET request for raw results

**Expected Assertions:**
- HTTP status code 200
- Raw format preserved exactly
- No transformation applied to data
- Debugging information included
- Original structure maintained
- Nested objects and arrays preserved

## 3. List All Submissions

### Scenario: Multiple Submissions Listing
**Preconditions:**
- Mock `results_store.list_all_submissions` to return submission list
- Multiple submissions exist in store
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/results/submissions`

**Expected Assertions:**
- HTTP status code 200
- Response contains:
  - `submissions`: array of submission URLs
  - `count`: number of submissions
- `results_store.list_all_submissions` called once
- Count matches array length
- All submissions included
- Field types correct (list and int)

### Scenario: Empty Submissions List
**Preconditions:**
- Mock `results_store.list_all_submissions` to return empty list
- No submissions exist in store
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/results/submissions`

**Expected Assertions:**
- HTTP status code 200
- Response contains:
  - `submissions`: empty array
  - `count`: 0
- Store method called correctly
- Empty state handled properly
- Count equals array length

### Scenario: Large Submissions List
**Preconditions:**
- Mock `results_store.list_all_submissions` with many submissions
- Store contains numerous submissions (100+ items)
- Clean application state

**User Actions:**
1. Send GET request for all submissions

**Expected Assertions:**
- HTTP status code 200
- All submissions included in response
- Count accurately reflects total
- Response processed efficiently
- First and last items correctly included
- No data truncation

## 4. Clear Submission Results

### Scenario: Successful Results Clearing
**Preconditions:**
- Mock `results_store.has_result` to return True
- Mock `results_store.clear_result` for successful clearing
- Valid submission exists in store
- Clean application state

**User Actions:**
1. Send DELETE request to `/api/v1/results/submission/test-submission-123`

**Expected Assertions:**
- HTTP status code 200
- Response contains: `{"message": "Results cleared for submission: test-submission-123"}`
- `results_store.has_result` called with correct submission_url
- `results_store.clear_result` called with correct submission_url
- Both methods called exactly once

### Scenario: Clear Non-Existent Submission
**Preconditions:**
- Mock `results_store.has_result` to return False
- Submission does not exist in store
- Clean application state

**User Actions:**
1. Send DELETE request to `/api/v1/results/submission/non-existent-submission`

**Expected Assertions:**
- HTTP status code 404
- HTTPException with detail: "No results found for submission: non-existent-submission"
- `results_store.has_result` called for validation
- `results_store.clear_result` not called
- No clearing attempted

### Scenario: Clear Results Validation Flow
**Preconditions:**
- Mock both store methods appropriately
- Valid submission for clearing
- Clean application state

**User Actions:**
1. Send DELETE request for existing submission

**Expected Assertions:**
- HTTP status code 200
- Both store methods called exactly once
- Correct parameters passed to both methods
- Validation occurs before clearing
- Success message returned

## 5. Results Store Integration

### Scenario: Store Method Integration
**Preconditions:**
- Mock all results_store methods
- Various submission states
- Clean application state

**User Actions:**
1. Test all endpoint operations in sequence

**Expected Assertions:**
- All store methods called correctly
- Parameters passed accurately
- Return values handled properly
- Method calls with expected parameters:
  - `get_result_transformed` called for transformed endpoint
  - `get_result` called for raw endpoint
  - `list_all_submissions` called for listing endpoint
  - `has_result` and `clear_result` called for delete endpoint

### Scenario: Store Exception Handling
**Preconditions:**
- Mock results_store methods to raise exceptions
- Valid request parameters
- Clean application state

**User Actions:**
1. Send requests that trigger store exceptions

**Expected Assertions:**
- Store exceptions propagate during testing
- Exception message matches expected pattern
- Test framework catches exceptions appropriately
- No silent failures

## 6. Response Format Validation

### Scenario: Transformed Results Format
**Preconditions:**
- Mock standardized results format
- Valid submission with complete analysis
- Clean application state

**User Actions:**
1. Send GET request for transformed results

**Expected Assertions:**
- Response follows list format (List[Dict[str, Any]])
- Each item in list is a dictionary
- Data integrity maintained
- Field values preserved correctly
- Type conversion handled correctly

### Scenario: Raw Results Format
**Preconditions:**
- Mock raw results format
- Valid submission with unprocessed data
- Clean application state

**User Actions:**
1. Send GET request for raw results

**Expected Assertions:**
- Response follows dict format (Dict[str, Any])
- Raw structure preserved exactly
- Nested data structures maintained
- Array data preserved
- No transformation applied

### Scenario: Submissions List Format
**Preconditions:**
- Mock submissions listing
- Multiple submissions in store
- Clean application state

**User Actions:**
1. Send GET request for submissions list

**Expected Assertions:**
- Response contains `submissions` and `count` fields
- `submissions` field is list type
- `count` field is integer type
- Count calculation accurate
- Response structure consistent

## 7. Error Handling

### Scenario: URL Encoding Handling
**Preconditions:**
- Mock results_store methods
- URL-encoded submission URLs
- Clean application state

**User Actions:**
1. Send GET request with URL-encoded characters

**Expected Assertions:**
- Request processed correctly
- URL decoding handled by FastAPI
- Store methods called with decoded URL
- Special characters handled properly
- Results retrieved or 404 returned appropriately

### Scenario: Invalid URL Characters
**Preconditions:**
- Mock results_store methods to return None
- URLs with special characters
- Clean application state

**User Actions:**
1. Send GET request with encoded special characters

**Expected Assertions:**
- HTTP status code 404 (for non-existent)
- Store called with properly decoded URL
- URL encoding/decoding works correctly
- No URL processing errors

## 8. Performance Considerations

### Scenario: Large Results Data
**Preconditions:**
- Mock results_store with large dataset (1000+ items)
- Submission with extensive analysis results
- Clean application state

**User Actions:**
1. Send GET request for large results

**Expected Assertions:**
- HTTP status code 200
- Large data handled efficiently
- All data items included in response
- Response length matches expected
- Data integrity maintained across large dataset
- First and last items correctly included

### Scenario: Concurrent Results Access
**Preconditions:**
- Mock results_store methods
- Multiple simultaneous requests
- Clean application state

**User Actions:**
1. Send multiple concurrent requests to various endpoints

**Expected Assertions:**
- All requests processed successfully
- HTTP status code 200 for all requests
- Store methods called correct number of times
- No race conditions in test environment
- Consistent response quality

## Integration Points to Verify

1. **Results Store Integration**
   - Proper store method calling
   - Parameter passing accuracy
   - Response handling and mapping
   - Mock verification working correctly

2. **Data Format Handling**
   - Transformed vs raw format distinction
   - Response serialization working
   - Type conversion handled correctly
   - Format consistency maintained

3. **Testing and Debugging Support**
   - Raw results access for debugging
   - Submissions listing for testing
   - Results clearing for test cleanup
   - Store state management through mocking

4. **API Contract Compliance**
   - Correct HTTP status codes
   - Proper error messages
   - Response format consistency
   - URL parameter handling 