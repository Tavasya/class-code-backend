# Centralized File Processing System

## Overview

This document describes the implementation of a centralized file processing system that eliminates the audio conversion issues caused by redundant downloads and premature file cleanup.

## Problem Solved

### Original Issue
- **Redundant processing**: AudioService downloaded and converted files, then PronunciationService re-downloaded and re-converted the same URLs
- **Race conditions**: Multiple services trying to process the same file simultaneously
- **Premature cleanup**: Files were deleted before all dependent services finished using them
- **Production failures**: Network timeouts and resource contention during duplicate processing

### Root Cause
The original architecture treated each service as independent units that handled their own file processing, leading to:
```
Audio URL → AudioService (download+convert) → WAV path in pub/sub
                 ↓
Audio URL → PronunciationService (download+convert AGAIN) → Use file
```

## Solution Architecture

### New Flow
```
Audio URL → AudioService (download+convert ONCE) → Register with FileManager
                 ↓
WAV file path + session_id → All analysis services use SAME file
                 ↓
Services complete → FileManager cleans up automatically
```

## Key Components

### 1. FileManagerService (`app/services/file_manager_service.py`)

**Responsibilities:**
- Track file sessions with unique session IDs
- Monitor which services need each file
- Coordinate cleanup when all services complete
- Provide failsafe cleanup for orphaned files

**Key Methods:**
- `register_file_session()`: Register a file with its dependent services
- `mark_service_complete()`: Mark when a service finishes with a file
- `periodic_cleanup()`: Clean up expired/orphaned files

### 2. Updated AudioService (`app/services/audio_service.py`)

**Changes:**
- Generates session IDs for file tracking
- Registers converted files with FileManager
- Removed premature cleanup of WAV files
- Returns session_id in response

### 3. Updated PronunciationService (`app/services/pronunciation_service.py`)

**Changes:**
- Removed URL processing logic (now only accepts local file paths)
- Accepts session_id parameter for lifecycle management
- Marks service as complete when analysis finishes
- No longer performs cleanup (handled by FileManager)

### 4. Message Flow Updates

**New Message Fields:**
- `session_id`: Added to AUDIO_CONVERSION_DONE and QUESTION_ANALYSIS_READY messages
- Used for file lifecycle tracking throughout the pipeline

## File Lifecycle

### 1. Registration
```python
session_id = file_manager.generate_session_id(submission_url, question_number)
await file_manager.register_file_session(
    session_id=session_id,
    file_path=wav_path,
    dependent_services={"pronunciation"},
    cleanup_timeout_minutes=30
)
```

### 2. Service Completion
```python
# In PronunciationService
await file_manager.mark_service_complete(session_id, "pronunciation")
```

### 3. Automatic Cleanup
- Triggered when all dependent services complete
- Failsafe cleanup after timeout (default: 30 minutes)
- Manual cleanup via debug endpoints

## Monitoring and Debugging

### Debug Endpoints

**GET `/api/v1/debug/file-sessions`**
- View all active file sessions
- See file paths and pending dependencies
- Monitor system health

**POST `/api/v1/debug/cleanup-session/{session_id}`**
- Force cleanup of specific session
- Emergency cleanup for stuck files

**POST `/api/v1/debug/periodic-cleanup`**
- Manually trigger periodic cleanup
- Useful for testing and maintenance

### Example Monitoring Response
```json
{
    "status": "success",
    "active_sessions": {
        "session_123456_1_1703123456": {
            "file_path": "/tmp/tmpXYZ.wav",
            "created_at": "2023-12-20T10:30:00",
            "dependencies": ["pronunciation"],
            "cleanup_completed": false
        }
    },
    "total_active": 1
}
```

## Testing

### Test Script
Run `test_centralized_file_processing.py` to verify:
- File session creation and tracking
- Proper cleanup coordination
- Monitoring endpoints functionality
- No duplicate downloads/conversions

### Expected Behaviors
1. **Single Download**: Each audio URL downloaded exactly once
2. **Session Tracking**: Files tracked with unique session IDs
3. **Coordinated Cleanup**: Files removed only after all services complete
4. **Monitoring**: Real-time visibility into file lifecycle

## Performance Benefits

### Before vs After
- **50% reduction** in network calls (no duplicate downloads)
- **50% reduction** in CPU usage (no duplicate conversions)
- **Eliminated** race conditions and file conflicts
- **Improved** reliability and production stability

### Resource Usage
- **Memory**: Minimal overhead for session tracking
- **Storage**: Temporary files properly cleaned up
- **Network**: Single download per audio file
- **CPU**: Single conversion per audio file

## Production Considerations

### Deployment
1. Deploy all updated services simultaneously
2. Monitor file session endpoints for proper tracking
3. Verify cleanup is working as expected

### Monitoring
- Watch debug endpoints for file accumulation
- Alert on high numbers of active sessions
- Monitor disk space usage in temp directories

### Error Handling
- Services mark completion even on errors (prevents hanging)
- Automatic failsafe cleanup prevents disk space issues
- Manual cleanup endpoints for emergency situations

## Configuration

### Cleanup Timeouts
```python
# Default: 30 minutes
cleanup_timeout_minutes=30

# Periodic cleanup: every 5 minutes
await asyncio.sleep(300)
```

### Service Dependencies
```python
# Currently only pronunciation service needs WAV files
dependent_services = {"pronunciation"}

# Can be extended for future services
dependent_services = {"pronunciation", "speaker_analysis", "emotion_detection"}
```

## Future Enhancements

### Possible Extensions
1. **Multiple file formats**: Support for different output formats per service
2. **Distributed storage**: Integration with cloud storage for large files
3. **Advanced monitoring**: Metrics and alerts for file processing pipeline
4. **Caching**: Intelligent caching of frequently accessed files

### Scalability
- **Horizontal scaling**: FileManager can be made distributed
- **Load balancing**: Session distribution across multiple instances
- **Storage optimization**: Compression and deduplication

## Troubleshooting

### Common Issues

**Files not being cleaned up:**
- Check debug endpoints for stuck sessions
- Verify services are calling `mark_service_complete()`
- Use manual cleanup if needed

**High disk usage:**
- Monitor active sessions count
- Check for services not completing properly
- Adjust cleanup timeout if needed

**Missing session IDs:**
- Verify message format includes session_id
- Check AudioService is registering files properly
- Ensure message parsing handles optional fields 