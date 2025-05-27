# Debug Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/debug_endpoint.py` - Debug endpoint implementation
- `app/services/file_manager_service.py` - File manager service integration
- `app/models/schemas.py` - Response models for debug endpoints
- `app/core/config.py` - Configuration and dependencies

## 1. Get Active File Sessions

### Scenario: Successful File Sessions Retrieval
**Preconditions:**
- Mock `file_manager.get_active_sessions` to return sessions data
- Multiple active file sessions exist
- Clean application state
- Mock session information

**User Actions:**
1. Send GET request to `/api/v1/debug/file-sessions`

**Expected Assertions:**
- HTTP status code 200
- Response contains:
  - `status`: "success"
  - `active_sessions`: dict of session information
  - `total_active`: number matching session count
- `file_manager.get_active_sessions` called correctly
- Session data properly formatted

### Scenario: No Active Sessions
**Preconditions:**
- Mock `file_manager.get_active_sessions` to return empty dict
- No active file sessions exist
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/debug/file-sessions`

**Expected Assertions:**
- HTTP status code 200
- Response contains:
  - `status`: "success"
  - `active_sessions`: empty dict
  - `total_active`: 0
- Empty state handled properly
- No errors with empty sessions

### Scenario: File Manager Error
**Preconditions:**
- Mock `file_manager.get_active_sessions` to raise exception
- File manager service unavailable
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/debug/file-sessions`

**Expected Assertions:**
- HTTP status code 500
- HTTPException with detail: "Error getting file sessions: [error message]"
- Error logged appropriately
- Exception handled gracefully

## 2. Force Cleanup Session

### Scenario: Successful Session Cleanup
**Preconditions:**
- Mock `file_manager.get_session_info` to return session data
- Mock `file_manager.force_cleanup_session` for successful cleanup
- Valid session ID exists
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/debug/cleanup-session/test-session-123`

**Expected Assertions:**
- HTTP status code 200
- Response contains:
  - `status`: "success"
  - `message`: "Forced cleanup of session test-session-123"
- `file_manager.get_session_info` called with correct session_id
- `file_manager.force_cleanup_session` called with correct session_id
- Session successfully cleaned up

### Scenario: Non-Existent Session Cleanup
**Preconditions:**
- Mock `file_manager.get_session_info` to return None
- Session ID does not exist
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/debug/cleanup-session/non-existent-session`

**Expected Assertions:**
- HTTP status code 404
- HTTPException with detail: "Session non-existent-session not found"
- `file_manager.get_session_info` called for validation
- `file_manager.force_cleanup_session` not called
- No cleanup attempted

### Scenario: Cleanup Operation Failure
**Preconditions:**
- Mock `file_manager.get_session_info` to return session data
- Mock `file_manager.force_cleanup_session` to raise exception
- Valid session exists but cleanup fails
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/debug/cleanup-session/failing-session`

**Expected Assertions:**
- HTTP status code 500
- HTTPException with detail: "Error cleaning up session: [error message]"
- Session existence validated first
- Cleanup attempted but failed
- Error logged appropriately

## 3. Trigger Periodic Cleanup

### Scenario: Successful Periodic Cleanup
**Preconditions:**
- Mock `file_manager.periodic_cleanup` for successful operation
- File manager service available
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/debug/periodic-cleanup`

**Expected Assertions:**
- HTTP status code 200
- Response contains:
  - `status`: "success"
  - `message`: "Periodic cleanup completed"
- `file_manager.periodic_cleanup` called correctly
- Cleanup operation completed successfully

### Scenario: Periodic Cleanup Failure
**Preconditions:**
- Mock `file_manager.periodic_cleanup` to raise exception
- File manager service encounters error
- Clean application state

**User Actions:**
1. Send POST request to `/api/v1/debug/periodic-cleanup`

**Expected Assertions:**
- HTTP status code 500
- HTTPException with detail: "Error in periodic cleanup: [error message]"
- Error logged appropriately with context
- Exception handled gracefully

### Scenario: Periodic Cleanup Performance
**Preconditions:**
- Mock `file_manager.periodic_cleanup` with processing delay
- Large number of files to clean up
- Clean application state

**User Actions:**
1. Send POST request for periodic cleanup

**Expected Assertions:**
- Request processed within reasonable time
- Cleanup operation handles large workload
- Response indicates completion
- No timeout issues

## 4. File Manager Integration

### Scenario: File Manager Service Availability
**Preconditions:**
- Mock file_manager service methods
- All service operations available
- Clean application state

**User Actions:**
1. Test all debug endpoints

**Expected Assertions:**
- All file_manager methods called correctly
- Service integration working properly
- Parameters passed accurately
- Return values handled appropriately

### Scenario: File Manager Service Degradation
**Preconditions:**
- Mock file_manager with intermittent failures
- Service experiencing issues
- Clean application state

**User Actions:**
1. Send requests during service issues

**Expected Assertions:**
- Errors handled gracefully
- Appropriate HTTP error responses
- Service issues logged
- System remains stable

## 5. Session Information Validation

### Scenario: Session Data Format Validation
**Preconditions:**
- Mock file_manager with complete session data
- Valid session with all metadata
- Clean application state

**User Actions:**
1. Send GET request for file sessions

**Expected Assertions:**
- Session data includes all required fields
- Session information properly formatted
- Metadata preserved correctly
- Data types consistent

### Scenario: Session State Consistency
**Preconditions:**
- Mock file_manager with various session states
- Sessions in different lifecycle stages
- Clean application state

**User Actions:**
1. Query sessions and perform cleanup operations

**Expected Assertions:**
- Session states accurately reflected
- State transitions handled correctly
- Consistency maintained across operations
- No state corruption

## 6. Error Handling and Logging

### Scenario: Comprehensive Error Logging
**Preconditions:**
- Mock file_manager methods to raise various exceptions
- Different error scenarios
- Logging configuration enabled

**User Actions:**
1. Trigger various error conditions

**Expected Assertions:**
- All errors logged with appropriate context
- Error messages include relevant details
- Log levels appropriate for error types
- Stack traces available for debugging

### Scenario: Error Response Consistency
**Preconditions:**
- Mock various error conditions
- Different failure scenarios
- Clean application state

**User Actions:**
1. Test error handling across all endpoints

**Expected Assertions:**
- Consistent error response format
- Appropriate HTTP status codes
- Error details properly formatted
- No sensitive information leaked

## 7. Security and Access Control

### Scenario: Debug Endpoint Access Validation
**Preconditions:**
- Debug endpoints available
- Various access scenarios
- Clean application state

**User Actions:**
1. Access debug endpoints from different contexts

**Expected Assertions:**
- Debug endpoints accessible (no authentication shown in code)
- Operations execute correctly
- No unauthorized access issues
- Debug functionality working

### Scenario: Session ID Validation
**Preconditions:**
- Mock file_manager for session operations
- Various session ID formats
- Clean application state

**User Actions:**
1. Test with different session ID formats

**Expected Assertions:**
- Session IDs processed correctly
- Invalid session IDs handled gracefully
- No injection vulnerabilities
- Proper validation performed

## 8. Performance and Monitoring

### Scenario: Debug Endpoint Performance
**Preconditions:**
- Mock file_manager with performance variations
- Various workload scenarios
- Clean application state

**User Actions:**
1. Test endpoints under different loads

**Expected Assertions:**
- Response times within acceptable limits
- Memory usage appropriate
- No performance degradation
- Scalable operation

### Scenario: Concurrent Debug Operations
**Preconditions:**
- Mock file_manager for concurrent access
- Multiple simultaneous requests
- Clean application state

**User Actions:**
1. Send concurrent requests to debug endpoints

**Expected Assertions:**
- All requests processed successfully
- No race conditions
- Consistent results
- Proper request isolation

## 9. Integration with File Management

### Scenario: File Lifecycle Monitoring
**Preconditions:**
- Mock file_manager with active file operations
- Files in various lifecycle stages
- Clean application state

**User Actions:**
1. Monitor file sessions during operations

**Expected Assertions:**
- File lifecycle accurately tracked
- Session information reflects current state
- Cleanup operations effective
- No file leaks

### Scenario: Resource Management Validation
**Preconditions:**
- Mock file_manager with resource tracking
- Various resource usage scenarios
- Clean application state

**User Actions:**
1. Test resource management through debug endpoints

**Expected Assertions:**
- Resource usage tracked correctly
- Cleanup operations free resources
- No resource leaks
- Efficient resource utilization

## Integration Points to Verify

1. **File Manager Service Integration**
   - Proper service method calling
   - Parameter passing accuracy
   - Response handling and mapping
   - Error propagation working correctly

2. **Debug Information Accuracy**
   - Session data reflects actual state
   - Cleanup operations effective
   - Monitoring information accurate
   - Debugging functionality useful

3. **Error Handling and Recovery**
   - Service errors handled gracefully
   - Appropriate error responses
   - System stability maintained
   - Recovery mechanisms working

4. **Performance and Scalability**
   - Debug operations efficient
   - Scalable under load
   - Resource usage appropriate
   - Response times acceptable 