# Service Chain Integration Tests

This directory contains integration tests for **Service Chain Integration** - testing how services work together in coordinated workflows, focusing on business logic coordination rather than infrastructure or message processing.

## Test Philosophy

These tests focus on **service-to-service coordination** by:
- ✅ Using real service instances (minimal mocking)
- ✅ Testing direct service method calls (bypassing pub/sub)
- ✅ Verifying data flows correctly between services
- ✅ Testing business logic coordination and state management
- ✅ Using real external APIs for realistic testing

## Test Structure

### 🔧 `conftest.py`
- Shared fixtures for all service chain tests
- Mock PubSubClient to prevent actual message publishing
- Real service instances and test data
- Standard test audio URL and transcript

### 🔗 `test_core_file_chain.py`
**Tests: AudioService → FileManager → PronunciationService coordination**
- Complete file lifecycle from audio processing to cleanup
- File coordination with multiple services
- Error handling while maintaining proper cleanup
- Concurrent file chains without interference

**Key Integration Points Tested:**
- AudioService creates files and registers with FileManager
- PronunciationService uses registered files with session_id
- FileManager coordinates cleanup when services complete
- Session management across service completion

### 🎯 `test_analysis_coordination.py` 
**Tests: AudioService + TranscriptionService → AnalysisCoordinator logic**
- Parallel service completion coordination
- Out-of-order completion handling
- Multi-question state management
- Error handling in coordination logic

**Key Integration Points Tested:**
- AnalysisCoordinatorService waits for both audio AND transcription
- Coordination state management across multiple questions
- Data integrity through coordination logic
- Analysis-ready message triggering

### 📊 `test_results_aggregation.py`
**Tests: All Analysis Services → Final Results Storage**
- Complete analysis pipeline to storage
- Results format consistency across services
- Partial failure handling
- Multi-question aggregation
- Cache and database storage consistency

**Key Integration Points Tested:**
- Pronunciation, Grammar, Lexical services produce compatible formats
- Results aggregation maintains data integrity
- ResultsStore (memory cache) and DatabaseService consistency
- Error handling preserves system stability

## Key Differences from Other Testing

### vs. Infrastructure Integration (existing)
| **Service Chain Integration** | **Infrastructure Integration** |
|------------------------------|--------------------------------|
| Tests service coordination | Tests external dependencies |
| Direct service method calls | Real API calls, file operations |
| Business logic focus | Infrastructure reliability focus |
| Service state management | Resource management |

### vs. Pub/Sub Message Integration (not implemented)
| **Service Chain Integration** | **Pub/Sub Message Integration** |
|------------------------------|--------------------------------|
| Direct service calls | Webhook message processing |
| Business logic coordination | Message parsing and routing |
| Service method interfaces | HTTP/JSON message interfaces |
| Data transformation | Message format validation |

## Running Tests

### Run all service chain tests:
```bash
pytest tests/int_testing/service_chain_testing/ -v
```

### Run specific test categories:
```bash
# Core file lifecycle tests
pytest tests/int_testing/service_chain_testing/test_core_file_chain.py -v

# Analysis coordination tests  
pytest tests/int_testing/service_chain_testing/test_analysis_coordination.py -v

# Results aggregation tests
pytest tests/int_testing/service_chain_testing/test_results_aggregation.py -v
```

### Run with specific markers:
```bash
# Run only the most critical tests
pytest tests/int_testing/service_chain_testing/ -v -k "lifecycle_chain or coordination or aggregation"

# Run tests that require external APIs
pytest tests/int_testing/service_chain_testing/ -v -k "analysis"
```

## Critical Service Chains Covered

### 🔧 **Chain 1: File Lifecycle Coordination**
```
AudioService.process_single_audio()
  ↓ (creates WAV file + session_id)
FileManagerService.register_file_session()
  ↓ (tracks file dependencies)
PronunciationService.analyze_pronunciation()
  ↓ (uses file + marks completion)
FileManagerService.mark_service_complete()
  ↓ (triggers cleanup)
File deletion
```

### 🎯 **Chain 2: Analysis Coordination**  
```
AudioService.process_single_audio() (parallel)
TranscriptionService.process_single_transcription() (parallel)
  ↓ (both complete)
AnalysisCoordinatorService.handle_audio_done()
AnalysisCoordinatorService.handle_transcription_done()
  ↓ (coordination logic)
Analysis services triggered with combined data
```

### 📊 **Chain 3: Results Aggregation**
```
PronunciationService.analyze_pronunciation()
GrammarService.analyze_grammar()
LexicalService.analyze_lexical_resources()
  ↓ (all complete)
Results aggregation logic
  ↓ (standardized format)
ResultsStore.store_result() (memory cache)
DatabaseService.update_submission_results() (persistent storage)
```

## Dependencies

### External Services
- **AssemblyAI**: Audio transcription (uses real API)
- **Azure Speech**: Pronunciation analysis (uses real API)  
- **OpenAI**: Grammar and lexical analysis (uses real API)
- **Supabase**: File storage and database (uses test environment)

### Python Packages
- `pytest-asyncio`: Async test support
- `unittest.mock`: Mocking PubSubClient only
- Standard service imports

## Mocking Strategy

### What IS Mocked ❌
- `PubSubClient.publish_message_by_name()` - Prevents actual message publishing
- `DatabaseService.update_submission_results()` - Prevents database writes in some tests

### What is NOT Mocked ✅
- All service business logic - uses real implementations
- File operations - tests real file coordination
- External API calls - uses real AssemblyAI, Azure, OpenAI APIs
- FileManagerService - tests real session coordination
- ResultsStore - tests real memory cache operations

## Test Data

### Shared Resources
- **Audio URL**: Real WebM file from Supabase recordings bucket
- **Transcript**: Standard test text for analysis services
- **Submission URLs**: Unique identifiers for each test case

### Test Isolation
- Each test uses unique submission URLs
- FileManager sessions are properly cleaned up
- ResultsStore is cleared after each test
- Temporary files are automatically cleaned up

## Success Criteria

These tests catch critical service coordination bugs:
- ✅ **File coordination failures** (production stability)
- ✅ **Analysis coordination bugs** (core business logic)
- ✅ **Result format inconsistencies** (customer-facing issues)
- ✅ **Data flow corruption** (service interface bugs)
- ✅ **State management errors** (session coordination bugs)

## Troubleshooting

### Common Issues

**Tests timing out:**
- Check external API keys are configured
- Verify network connectivity to Supabase/AssemblyAI/Azure/OpenAI
- Increase timeout values for slow networks

**File cleanup assertions failing:**
- Check FileManagerService is properly cleaning up sessions
- Verify async cleanup timing (may need longer sleep values)
- Check for file permission issues

**Coordination state errors:**
- Verify AnalysisCoordinatorService state management
- Check message object creation matches expected format
- Verify mocking of PubSubClient is working correctly

**Results format inconsistencies:**
- Check that all analysis services return standardized format
- Verify grade and issues fields are present and valid
- Check data type consistency across services

This testing approach ensures your critical service coordination workflows are thoroughly tested while remaining focused and maintainable. 