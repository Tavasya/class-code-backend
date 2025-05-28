# File Management Testing Integration Test Plan

## Files to Reference
- `tests/int_testing/file_management_testing/test_file_lifecycle_integration.py` - File lifecycle and session management tests
- `tests/int_testing/file_management_testing/test_supabase_storage_integration.py` - Supabase storage integration tests
- `tests/int_testing/file_management_testing/test_format_conversion_integration.py` - Audio format conversion tests
- `tests/int_testing/file_management_testing/test_audio_download_integration.py` - Audio download and processing tests
- `tests/int_testing/file_management_testing/test_end_to_end_integration.py` - End-to-end file management tests
- `tests/int_testing/file_management_testing/conftest.py` - Test fixtures and utilities
- `app/services/file_manager_service.py` - File lifecycle management service

## Test Setup
- Uses temporary directories for file operations
- Uses `AsyncMock` for external storage services
- Tests use `temp_dir` fixture for isolated file operations
- All tests are async and use `@pytest.mark.asyncio`
- Automatic cleanup of test files and sessions

## 1. File Lifecycle Integration

### Scenario: Complete File Lifecycle Management
**Test Method:** `test_complete_file_lifecycle`
**Preconditions:**
- Temporary directory for test files
- Clean file manager state
- Valid session configuration

**Integration Flow:**
1. Create test audio file in temporary directory
2. Register file session with dependent services
3. Mark services complete one by one
4. Verify file cleanup after all services complete
5. Verify session marked as cleanup completed

**Expected Assertions:**
- File session registers correctly with metadata
- File exists during active session
- Partial service completion doesn't trigger cleanup
- Final service completion triggers automatic cleanup
- Session state properly tracks completion status

### Scenario: Multiple Sessions Concurrent Management
**Test Method:** `test_multiple_sessions_concurrent`
**Preconditions:**
- Multiple test files in temporary directory
- Clean file manager state
- Different session configurations

**Integration Flow:**
1. Create multiple test audio files
2. Register multiple file sessions concurrently
3. Complete services in different orders across sessions
4. Verify independent session management
5. Verify all files cleaned up correctly

**Expected Assertions:**
- Multiple sessions operate independently
- No interference between concurrent sessions
- Service completion tracking works per session
- Cleanup occurs independently for each session
- Session isolation maintained throughout lifecycle

### Scenario: Session Cleanup Timeout Handling
**Test Method:** `test_session_cleanup_timeout`
**Preconditions:**
- Test file in temporary directory
- Very short timeout configuration (0.01 minutes)
- Clean file manager state

**Integration Flow:**
1. Register file session with short timeout
2. Wait for timeout period to expire
3. Run periodic cleanup process
4. Verify file cleaned up due to timeout
5. Verify session removed from tracking

**Expected Assertions:**
- Timeout mechanism triggers correctly
- Periodic cleanup removes expired sessions
- Files cleaned up when sessions timeout
- Session tracking updated after timeout cleanup
- System remains stable after timeout operations

### Scenario: Force Cleanup Session
**Test Method:** `test_force_cleanup_session`
**Preconditions:**
- Test file in temporary directory
- Active session with long timeout
- Clean file manager state

**Integration Flow:**
1. Register file session with long timeout
2. Force cleanup before natural completion
3. Verify immediate file cleanup
4. Verify session removed from tracking
5. Test system stability after force cleanup

**Expected Assertions:**
- Force cleanup works immediately regardless of timeout
- File removed from filesystem
- Session removed from active tracking
- No side effects on other sessions
- System continues operating normally

### Scenario: Session Management with Unknown Sessions
**Test Method:** `test_service_completion_with_unknown_session`
**Preconditions:**
- Clean file manager state
- Non-existent session ID

**Integration Flow:**
1. Attempt to mark service complete for unknown session
2. Verify graceful handling of unknown session
3. Test system stability with invalid operations
4. Verify no side effects on valid sessions

**Expected Assertions:**
- Unknown session operations return False
- No errors or exceptions thrown
- System remains stable with invalid inputs
- Valid sessions unaffected by invalid operations
- Proper error handling for edge cases

### Scenario: Active Sessions Information Retrieval
**Test Method:** `test_get_active_sessions`
**Preconditions:**
- Clean file manager state initially
- Test file for session creation

**Integration Flow:**
1. Verify initially no active sessions
2. Create and register file session
3. Retrieve active sessions information
4. Verify session data accuracy
5. Complete session and verify removal

**Expected Assertions:**
- Initial state shows no active sessions
- Active session appears in session list
- Session data includes correct metadata
- Session dependencies tracked accurately
- Completed sessions removed from active list

## 2. Supabase Storage Integration

### Scenario: File Upload to Supabase Storage
**Test Method:** `test_supabase_file_upload`
**Preconditions:**
- Mock Supabase storage client
- Test audio file for upload
- Valid storage bucket configuration

**Integration Flow:**
1. Upload test file to Supabase storage
2. Verify upload success response
3. Check file metadata and storage path
4. Verify file accessible via storage URL
5. Test error handling for upload failures

**Expected Assertions:**
- File uploads successfully to Supabase
- Upload response includes correct metadata
- Storage path follows expected format
- File accessible via generated URL
- Error handling works for failed uploads

### Scenario: File Download from Supabase Storage
**Test Method:** `test_supabase_file_download`
**Preconditions:**
- Mock Supabase storage client
- Pre-uploaded file in storage
- Local download directory

**Integration Flow:**
1. Download file from Supabase storage
2. Verify file downloaded to local filesystem
3. Check file integrity and content
4. Verify download metadata
5. Test error handling for download failures

**Expected Assertions:**
- File downloads successfully from Supabase
- Downloaded file matches original content
- Local file created in correct location
- Download metadata accurate
- Error handling works for failed downloads

### Scenario: Storage Cleanup and File Deletion
**Test Method:** `test_supabase_storage_cleanup`
**Preconditions:**
- Mock Supabase storage client
- Files uploaded to storage
- Storage cleanup configuration

**Integration Flow:**
1. Upload multiple files to storage
2. Trigger storage cleanup process
3. Verify files deleted from storage
4. Check cleanup logs and metadata
5. Test error handling for deletion failures

**Expected Assertions:**
- Files deleted successfully from storage
- Cleanup process completes without errors
- Storage space freed correctly
- Cleanup logs accurate and complete
- Error handling works for deletion failures

## 3. Format Conversion Integration

### Scenario: Audio Format Conversion Chain
**Test Method:** `test_audio_format_conversion_chain`
**Preconditions:**
- Test audio file in non-WAV format
- Format conversion service available
- Temporary directory for output

**Integration Flow:**
1. Start with audio file in original format (e.g., MP3, WebM)
2. Convert to WAV format for analysis
3. Verify conversion success and file quality
4. Check output file properties (sample rate, channels)
5. Test cleanup of intermediate files

**Expected Assertions:**
- Format conversion completes successfully
- Output file in correct WAV format
- Audio quality preserved during conversion
- File properties match requirements
- Intermediate files cleaned up properly

### Scenario: Batch Format Conversion
**Test Method:** `test_batch_format_conversion`
**Preconditions:**
- Multiple audio files in different formats
- Format conversion service available
- Temporary directory for outputs

**Integration Flow:**
1. Convert multiple files concurrently
2. Verify all conversions complete successfully
3. Check output file quality and properties
4. Test resource management during batch processing
5. Verify cleanup of all intermediate files

**Expected Assertions:**
- All files convert successfully
- Concurrent conversion works without interference
- Output quality consistent across files
- Resource usage managed properly
- Complete cleanup after batch processing

### Scenario: Format Conversion Error Handling
**Test Method:** `test_format_conversion_error_handling`
**Preconditions:**
- Corrupted or invalid audio file
- Format conversion service available
- Error handling configuration

**Integration Flow:**
1. Attempt conversion of invalid audio file
2. Verify graceful error handling
3. Check error messages and logging
4. Test system stability after conversion errors
5. Verify cleanup occurs even with errors

**Expected Assertions:**
- Invalid files handled gracefully
- Appropriate error messages generated
- System remains stable after errors
- Cleanup occurs despite conversion failures
- Error logging accurate and helpful

## 4. Audio Download Integration

### Scenario: Audio Download and Processing Chain
**Test Method:** `test_audio_download_processing_chain`
**Preconditions:**
- Valid audio URL for download
- Download service configuration
- Temporary directory for downloads

**Integration Flow:**
1. Download audio file from URL
2. Verify download success and file integrity
3. Process downloaded file (format conversion if needed)
4. Register file with session management
5. Test cleanup after processing

**Expected Assertions:**
- Audio downloads successfully from URL
- Downloaded file integrity verified
- Processing completes without errors
- File registered correctly with session manager
- Cleanup occurs after processing complete

### Scenario: Download Error Handling and Retry
**Test Method:** `test_download_error_handling_retry`
**Preconditions:**
- Invalid or unreachable audio URL
- Download retry configuration
- Error handling settings

**Integration Flow:**
1. Attempt download from invalid URL
2. Verify retry mechanism triggers
3. Test maximum retry limit handling
4. Check error logging and reporting
5. Verify system stability after failed downloads

**Expected Assertions:**
- Retry mechanism works correctly
- Maximum retries respected
- Appropriate error messages generated
- System remains stable after failures
- Error reporting accurate and complete

### Scenario: Concurrent Audio Downloads
**Test Method:** `test_concurrent_audio_downloads`
**Preconditions:**
- Multiple valid audio URLs
- Download service configuration
- Temporary directory for downloads

**Integration Flow:**
1. Start multiple downloads concurrently
2. Verify all downloads complete successfully
3. Check download performance and resource usage
4. Test file integrity for all downloads
5. Verify proper cleanup of all files

**Expected Assertions:**
- Concurrent downloads work without interference
- All files download successfully
- Resource usage managed properly
- File integrity maintained for all downloads
- Complete cleanup after all downloads

## 5. End-to-End File Management Integration

### Scenario: Complete File Management Workflow
**Test Method:** `test_complete_file_management_workflow`
**Preconditions:**
- Audio URL for download
- All file management services available
- Clean system state

**Integration Flow:**
1. Download audio file from URL
2. Convert to required format (WAV)
3. Register with session management
4. Process through analysis services
5. Clean up all files and sessions

**Expected Assertions:**
- Complete workflow executes successfully
- All integration points work correctly
- File transformations maintain quality
- Session management coordinates properly
- Final cleanup completes successfully

### Scenario: Multi-File Workflow with Dependencies
**Test Method:** `test_multi_file_workflow_dependencies`
**Preconditions:**
- Multiple audio files with different requirements
- Complex dependency configuration
- Clean system state

**Integration Flow:**
1. Process multiple files with different service dependencies
2. Verify dependency tracking works correctly
3. Test coordination between different workflows
4. Check resource sharing and isolation
5. Verify cleanup coordination across workflows

**Expected Assertions:**
- Multiple workflows process independently
- Dependencies tracked correctly per workflow
- Resource sharing works without conflicts
- Coordination handles complex scenarios
- Cleanup works across all workflows

## Integration Points Verified

1. **File Lifecycle Management**
   - Session creation, tracking, and cleanup coordination
   - Service dependency management and completion tracking
   - Timeout handling and force cleanup mechanisms

2. **Storage Integration**
   - Supabase storage upload, download, and cleanup operations
   - File integrity verification and metadata management
   - Error handling for storage operations

3. **Format Processing**
   - Audio format conversion and quality preservation
   - Batch processing and concurrent operations
   - Error handling for conversion failures

4. **Download Management**
   - URL-based audio download and retry mechanisms
   - Concurrent download coordination
   - Error handling and system stability

## Test Coverage Summary

The file management testing covers:
- ✅ Complete file lifecycle management and session tracking
- ✅ Concurrent session management and isolation
- ✅ Timeout and force cleanup mechanisms
- ✅ Supabase storage integration (upload, download, cleanup)
- ✅ Audio format conversion and quality preservation
- ✅ Audio download and retry mechanisms
- ✅ End-to-end file management workflows
- ✅ Error handling and system stability
- ❌ Performance testing with large files (not implemented)
- ❌ Storage quota management (not implemented)
- ❌ File compression and optimization (not implemented) 