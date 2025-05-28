# Debug Endpoint API Test Implementation

## Files Referenced
- `tests/test_debug_endpoint.py` - Complete test implementation
- `app/api/v1/endpoints/debug_endpoint.py` - Debug endpoint implementation
- `app/services/file_manager_service.py` - File manager service integration
- `app/models/schemas.py` - Response models for debug endpoints
- `app/core/config.py` - Configuration and dependencies

## Test Structure

### Test Class: `TestDebugEndpoint`
All tests are organized under a single test class with proper mocking setup.

### Mock Setup
```python
@pytest.fixture
def mock_file_manager():
    """Mock file_manager for testing"""
    with patch('app.api.v1.endpoints.debug_endpoint.file_manager') as mock:
        yield mock
```

## 1. Get Active File Sessions Tests

### `test_get_active_file_sessions_success`
**Purpose:** Test successful retrieval of active file sessions

**Mock Setup:**
- Returns multiple active sessions with complete metadata
- Sessions in different states (active, processing, idle)
- Includes files, timestamps, and status information

**Test Data:**
```json
{
  "session-001": {
    "created_at": "2024-01-01T12:00:00Z",
    "files": ["file1.mp3", "file2.wav"],
    "status": "active"
  },
  "session-002": {
    "created_at": "2024-01-01T12:05:00Z", 
    "files": ["file3.mp3"],
    "status": "processing"
  },
  "session-003": {
    "created_at": "2024-01-01T12:10:00Z",
    "files": [],
    "status": "idle"
  }
}
```

**Expected Response Structure:**
```json
{
  "status": "success",
  "active_sessions": {
    "session-001": {
      "created_at": "2024-01-01T12:00:00Z",
      "files": ["file1.mp3", "file2.wav"],
      "status": "active"
    }
  },
  "total_active": 3
}
```

**Assertions:**
- HTTP status code 200
- Response contains `status`: "success"
- `active_sessions` dict with all session data
- `total_active` count matches session count (3)
- All session IDs present in response
- Session details include files, status, and timestamps
- `file_manager.get_active_sessions` called once

### `test_get_active_file_sessions_empty`
**Purpose:** Test retrieval when no active sessions exist

**Mock Setup:**
- Returns empty dict from file manager

**Assertions:**
- HTTP status code 200
- Response `status`: "success"
- `active_sessions`: empty dict
- `total_active`: 0
- Method called correctly

### `test_get_active_file_sessions_error`
**Purpose:** Test handling of file manager error

**Mock Setup:**
- `file_manager.get_active_sessions` raises `Exception("File manager connection failed")`

**Assertions:**
- HTTP status code 500
- Error message: "Error getting file sessions: File manager connection failed"
- Method called once

### `test_get_active_file_sessions_large_dataset`
**Purpose:** Test handling of large number of active sessions (100+ sessions)

**Mock Setup:**
- Generates 100 sessions with different statuses
- Sessions named `session-000` through `session-099`

**Assertions:**
- HTTP status code 200
- `total_active`: 100
- All sessions included in response
- First session (`session-000`) and last session (`session-099`) present
- Response processed efficiently

## 2. Force Cleanup Session Tests

### `test_force_cleanup_session_success`
**Purpose:** Test successful session cleanup with validation flow

**Mock Setup:**
- `file_manager.get_session_info` returns session data
- `file_manager.force_cleanup_session` as AsyncMock for successful cleanup

**Test Data:**
```json
{
  "session_id": "test-session-123",
  "created_at": "2024-01-01T12:00:00Z",
  "files": ["file1.mp3", "file2.wav"],
  "status": "active"
}
```

**Expected Response Structure:**
```json
{
  "status": "success",
  "message": "Forced cleanup of session test-session-123"
}
```

**Assertions:**
- HTTP status code 200
- Response contains success status and message
- `file_manager.get_session_info` called with correct session_id
- `file_manager.force_cleanup_session` called with correct session_id
- Both methods called exactly once
- Session validation occurs before cleanup

### `test_force_cleanup_session_not_found`
**Purpose:** Test cleanup of non-existent session

**Mock Setup:**
- `file_manager.get_session_info` returns None
- `file_manager.force_cleanup_session` as AsyncMock (not called)

**Assertions:**
- HTTP status code 404
- Error message: "Session non-existent-session not found"
- `get_session_info` called for validation
- `force_cleanup_session` not called
- Validation flow working correctly

### `test_force_cleanup_session_cleanup_failure`
**Purpose:** Test cleanup operation failure

**Mock Setup:**
- `file_manager.get_session_info` returns session data
- `file_manager.force_cleanup_session` raises `Exception("Cleanup operation failed")`

**Assertions:**
- HTTP status code 500
- Error message: "Error cleaning up session: Cleanup operation failed"
- Session existence validated first
- Both methods called correctly
- Error message includes specific exception details

### `test_force_cleanup_session_special_characters`
**Purpose:** Test cleanup with special characters in session ID

**Test Data:**
- Session ID: `"test-session-with-special-chars!@#"`
- URL encoded for request

**Mock Setup:**
- Session exists with special character ID
- Successful cleanup

**Assertions:**
- HTTP status code 200
- URL decoding handled by FastAPI
- File manager called with decoded session ID
- Special characters processed correctly

## 3. Trigger Periodic Cleanup Tests

### `test_trigger_periodic_cleanup_success`
**Purpose:** Test successful periodic cleanup

**Mock Setup:**
- `file_manager.periodic_cleanup` as AsyncMock for successful operation

**Expected Response Structure:**
```json
{
  "status": "success",
  "message": "Periodic cleanup completed"
}
```

**Assertions:**
- HTTP status code 200
- Response contains success status and message
- `file_manager.periodic_cleanup` called once

### `test_trigger_periodic_cleanup_failure`
**Purpose:** Test periodic cleanup failure

**Mock Setup:**
- `file_manager.periodic_cleanup` raises `Exception("Periodic cleanup failed")`

**Assertions:**
- HTTP status code 500
- Error message: "Error in periodic cleanup: Periodic cleanup failed"
- Method called once
- Error message includes specific exception details

### `test_trigger_periodic_cleanup_performance`
**Purpose:** Test periodic cleanup with simulated processing delay

**Mock Setup:**
- Async function with `asyncio.sleep(0.1)` to simulate processing time

**Assertions:**
- HTTP status code 200
- Request processed successfully despite delay
- Async operation handled correctly
- No timeout issues

## 4. File Manager Integration Tests

### `test_file_manager_service_integration`
**Purpose:** Test integration with file manager service across all endpoints

**Mock Setup:**
- All file_manager methods properly mocked
- Successful responses for all operations

**Test Flow:**
1. GET `/api/v1/debug/file-sessions`
2. POST `/api/v1/debug/cleanup-session/test-session`
3. POST `/api/v1/debug/periodic-cleanup`

**Assertions:**
- All endpoints return HTTP 200
- All file_manager methods called correctly:
  - `get_active_sessions` called for sessions endpoint
  - `get_session_info` and `force_cleanup_session` called for cleanup endpoint
  - `periodic_cleanup` called for cleanup endpoint
- Parameters passed accurately
- Return values handled appropriately

### `test_file_manager_service_degradation`
**Purpose:** Test handling of intermittent file manager failures

**Mock Setup:**
- `get_active_sessions` raises `Exception("Service temporarily unavailable")`
- `periodic_cleanup` raises `Exception("Service degraded")`

**Assertions:**
- Both endpoints return HTTP 500
- Error messages include service error details
- System remains stable during service issues

## 5. Session Information Validation Tests

### `test_session_data_format_validation`
**Purpose:** Test validation of session data format with complete metadata

**Mock Setup:**
- Complete session data with all metadata fields

**Test Data:**
```json
{
  "session-complete": {
    "session_id": "session-complete",
    "created_at": "2024-01-01T12:00:00Z",
    "last_accessed": "2024-01-01T12:30:00Z",
    "files": ["file1.mp3", "file2.wav"],
    "status": "active",
    "metadata": {
      "user_id": "user123",
      "upload_count": 2,
      "total_size": 1024000
    }
  }
}
```

**Assertions:**
- HTTP status code 200
- All required fields present in session data
- Data types consistent (lists, dicts, strings)
- Nested structures maintained
- Metadata preserved correctly

### `test_session_state_consistency`
**Purpose:** Test session state consistency across operations

**Mock Setup:**
- Sessions in different states (active, processing, idle)
- Consistent state representation

**Test Flow:**
1. Query sessions via GET endpoint
2. Cleanup a session via POST endpoint

**Assertions:**
- Session states accurately reflected
- Different statuses preserved
- Consistency maintained across operations
- No state corruption

## 6. Error Handling Tests

### `test_comprehensive_error_logging`
**Purpose:** Test error logging across different scenarios

**Test Scenarios:**
- Database connection failed
- Disk space insufficient
- Various service exceptions

**Assertions:**
- All errors result in HTTP 500 responses
- Error messages include specific exception details
- Exception handling consistent across endpoints
- No silent failures

### `test_error_response_consistency`
**Purpose:** Test consistency of error responses across endpoints

**Mock Setup:**
- Different error conditions (500, 404)
- Various failure scenarios

**Test Flow:**
1. GET endpoint with service error (500)
2. POST cleanup with non-existent session (404)
3. POST periodic cleanup with service error (500)

**Assertions:**
- Appropriate HTTP status codes (404, 500)
- All responses have `detail` field
- Error details properly formatted
- Consistent error response format

## 7. Performance Tests

### `test_debug_endpoint_performance`
**Purpose:** Test performance of debug endpoints

**Mock Setup:**
- Normal operations with standard responses

**Test Flow:**
- Time all three endpoints sequentially

**Assertions:**
- All requests complete successfully (HTTP 200)
- Total response time < 1 second (with mocks)
- Efficient operation

### `test_concurrent_debug_operations`
**Purpose:** Test concurrent access to debug endpoints

**Test Setup:**
- 10 concurrent requests alternating between endpoints

**Assertions:**
- All requests return HTTP 200
- Methods called correct number of times (5 each)
- No race conditions in test environment
- Consistent results across requests

## 8. File Management Integration Tests

### `test_file_lifecycle_monitoring`
**Purpose:** Test monitoring of file lifecycle through debug endpoints

**Mock Setup:**
- Sessions with files in various lifecycle stages
- Different file counts per session

**Test Data:**
```json
{
  "session-uploading": {
    "status": "uploading",
    "files": ["temp_file1.mp3"],
    "lifecycle_stage": "upload_in_progress"
  },
  "session-processing": {
    "status": "processing", 
    "files": ["file2.wav", "file3.mp3"],
    "lifecycle_stage": "analysis_in_progress"
  },
  "session-completed": {
    "status": "completed",
    "files": ["final_file.mp3"],
    "lifecycle_stage": "analysis_complete"
  }
}
```

**Assertions:**
- HTTP status code 200
- File lifecycle information accurately tracked
- Lifecycle stages properly represented
- File counts per session correct
- Status information consistent

### `test_resource_management_validation`
**Purpose:** Test resource management through debug endpoints

**Mock Setup:**
- Sessions with different resource usage patterns
- Resource tracking data included

**Test Data:**
```json
{
  "session-heavy": {
    "status": "active",
    "files": ["large_file1.mp3", "large_file2.wav"],
    "resource_usage": {
      "memory_mb": 512,
      "disk_space_mb": 1024,
      "cpu_percent": 25.5
    }
  },
  "session-light": {
    "status": "idle",
    "files": ["small_file.mp3"],
    "resource_usage": {
      "memory_mb": 64,
      "disk_space_mb": 128,
      "cpu_percent": 2.1
    }
  }
}
```

**Test Flow:**
1. Monitor resource usage via GET endpoint
2. Cleanup resource-heavy session via POST endpoint

**Assertions:**
- Resource usage information available
- Different usage patterns reflected
- Resource data properly formatted
- Cleanup operations target resource-heavy sessions

## Integration Points Verified

1. **File Manager Service Integration**
   - Proper service method calling
   - Parameter passing accuracy
   - Response handling and mapping
   - Mock verification working correctly

2. **Debug Information Accuracy**
   - Session data reflects mocked state
   - Cleanup operations properly mocked
   - Monitoring information accurate
   - Debugging functionality testable

3. **Error Handling and Recovery**
   - Service errors handled gracefully
   - Appropriate error responses (404, 500)
   - System stability maintained
   - Error messages informative

4. **Performance and Scalability**
   - Debug operations efficient with mocks
   - Scalable under simulated load
   - Resource usage appropriate
   - Response times acceptable (< 1 second)

5. **API Contract Compliance**
   - Correct HTTP status codes
   - Proper error messages
   - Response format consistency
   - URL parameter handling (encoding/decoding) 