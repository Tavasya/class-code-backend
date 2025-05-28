# File Management Integration Tests

This directory contains integration tests for the file management system, focusing on testing real interactions between services and external systems.

## Test Structure

### 🔧 `conftest.py`
- Shared fixtures for all file management tests
- Real audio URL and submission URL for testing
- Common service instances and test utilities

### 📥 `test_audio_download_integration.py`
**Tests audio download operations from Supabase storage:**
- Valid file downloads with proper cleanup
- Error handling for invalid/404 URLs
- Concurrent download operations
- Temporary file cleanup on failures

### 🔄 `test_format_conversion_integration.py`
**Tests FFmpeg audio format conversion:**
- WebM to WAV conversion with quality verification
- Error handling for corrupted/invalid files
- FFmpeg availability and dependency checks
- Cleanup of original files after conversion
- Concurrent conversion operations

### 🗂️ `test_file_lifecycle_integration.py`
**Tests file session management and lifecycle:**
- Complete file registration → service use → cleanup workflow
- Session ID generation with guaranteed uniqueness
- Multiple concurrent sessions with proper isolation
- Timeout-based cleanup for orphaned files
- Force cleanup for error scenarios
- Session information tracking and monitoring

### 🌐 `test_supabase_storage_integration.py`
**Tests Supabase integration (focused on actual usage):**
- Error handling for storage operations
- Database submission operations using real test submission
- Public access to recordings bucket via HTTP URLs

### 🚀 `test_end_to_end_integration.py`
**End-to-end workflow tests:**
- Complete audio processing: download → convert → register → cleanup
- Multiple concurrent audio processing workflows
- Error handling and recovery in complex workflows
- Service failure scenarios and cleanup behavior
- Session timeout behavior in real workflows
- File system integration with temporary directories

## Test Data

### Real Test Resources
- **Audio URL**: Uses actual WebM file from Supabase recordings bucket
- **Submission URL**: Uses real submission ID for database operations
- **No Mock Data**: Tests against actual services and storage

## Running Tests

### Run all file management tests:
```bash
pytest tests/int_testing/file_management_testing/ -v
```

### Run specific test categories:
```bash
# Audio download tests only
pytest tests/int_testing/file_management_testing/test_audio_download_integration.py -v

# Format conversion tests only
pytest tests/int_testing/file_management_testing/test_format_conversion_integration.py -v

# File lifecycle tests only
pytest tests/int_testing/file_management_testing/test_file_lifecycle_integration.py -v

# Supabase integration tests only
pytest tests/int_testing/file_management_testing/test_supabase_storage_integration.py -v

# End-to-end workflow tests only
pytest tests/int_testing/file_management_testing/test_end_to_end_integration.py -v
```

## Key Integration Points Tested

### 🔗 **AudioService ↔ File System**
- HTTP downloads from Supabase public URLs
- FFmpeg integration for format conversion
- Temporary file creation and cleanup

### 🔗 **FileManagerService ↔ Session Management**
- Unique session ID generation using UUID components
- File registration and dependency tracking
- Service completion and automatic cleanup
- Concurrent session isolation

### 🔗 **DatabaseService ↔ Supabase Database**
- Real submission result updates
- Error handling for missing submissions
- Data persistence verification

### 🔗 **File System ↔ Cleanup Operations**
- Automatic file cleanup after service completion
- Timeout-based orphaned file cleanup
- Error recovery and force cleanup scenarios

## Dependencies

### External Services
- **Supabase**: Database and storage access
- **FFmpeg**: Audio format conversion
- **HTTP Client**: Audio file downloads

### Python Packages
- `pytest-asyncio`: Async test support
- `aiohttp`: HTTP client for downloads
- `tempfile`: Temporary file management

## Test Philosophy

These integration tests focus on **real system behavior** rather than mocked interactions:

- ✅ Uses actual Supabase storage URLs
- ✅ Tests real FFmpeg conversion
- ✅ Exercises actual file system operations
- ✅ Tests real database operations
- ✅ No legacy upload functionality testing

This ensures the file management system works correctly with real external dependencies and handles edge cases that might not appear in unit tests. 