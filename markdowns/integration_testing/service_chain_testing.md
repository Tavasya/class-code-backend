# Service Chain Testing Integration Test Plan

## Files to Reference
- `tests/int_testing/service_chain_testing/test_core_file_chain.py` - Core file lifecycle chain tests
- `tests/int_testing/service_chain_testing/test_results_aggregation.py` - Results aggregation and coordination tests
- `tests/int_testing/service_chain_testing/test_analysis_coordination.py` - Analysis service coordination tests
- `tests/int_testing/service_chain_testing/conftest.py` - Test fixtures and utilities
- `app/services/audio_service.py` - Audio processing service
- `app/services/file_manager_service.py` - File lifecycle management
- `app/services/pronunciation_service.py` - Pronunciation analysis service

## Test Setup
- Uses real service instances for integration testing
- Uses `AsyncMock` for external API dependencies
- Tests use temporary directories for file operations
- All tests are async and use `@pytest.mark.asyncio`
- File cleanup handled automatically by fixtures

## 1. Core File Lifecycle Chain

### Scenario: Complete Audio File to Pronunciation Analysis Chain
**Test Method:** `test_audio_file_pronunciation_lifecycle_chain`
**Preconditions:**
- Valid audio URL for processing
- Clean file system state
- Mock external pronunciation API

**Integration Flow:**
1. AudioService processes audio URL → creates WAV file
2. FileManager registers file with session tracking
3. PronunciationService analyzes the registered file
4. FileManager automatically cleans up after service completion

**Expected Assertions:**
- Audio processing creates valid WAV file
- File is properly registered with FileManager
- Session tracking includes correct metadata
- Pronunciation analysis completes successfully
- File is automatically cleaned up after analysis
- Session marked as cleanup completed

### Scenario: File Chain with Multiple Service Coordination
**Test Method:** `test_file_chain_with_service_coordination`
**Preconditions:**
- Valid audio URL for processing
- Multiple dependent services (pronunciation, fluency)
- Clean file system state

**Integration Flow:**
1. AudioService processes audio and registers with multiple dependencies
2. First service (pronunciation) completes analysis
3. Verify file still exists (waiting for fluency service)
4. Second service (fluency) completes
5. Verify file is cleaned up after all services complete

**Expected Assertions:**
- File persists while services are still pending
- Session tracks multiple service dependencies correctly
- File cleanup waits for ALL services to complete
- Proper coordination between service completion signals
- Final cleanup occurs only after all dependencies satisfied

### Scenario: Error Handling in File Chain
**Test Method:** `test_file_chain_error_handling`
**Preconditions:**
- Valid audio URL for processing
- Invalid analysis parameters (empty reference text)
- Clean file system state

**Integration Flow:**
1. AudioService processes audio successfully
2. PronunciationService encounters error during analysis
3. Verify service still marks completion for cleanup
4. Verify file cleanup occurs despite service errors

**Expected Assertions:**
- Audio processing succeeds despite downstream errors
- Service errors don't prevent cleanup coordination
- File cleanup occurs even when services fail
- Error handling maintains system stability
- Session completion tracking works with errors

### Scenario: Concurrent File Chains
**Test Method:** `test_concurrent_file_chains`
**Preconditions:**
- Multiple audio URLs for concurrent processing
- Clean file system state
- Mock pronunciation service

**Integration Flow:**
1. Process multiple audio files concurrently
2. Run pronunciation analysis on all files concurrently
3. Verify no interference between concurrent chains
4. Verify all files are cleaned up properly

**Expected Assertions:**
- Concurrent audio processing succeeds without interference
- File registration handles concurrent sessions correctly
- Pronunciation analysis works on multiple files simultaneously
- Cleanup coordination works for concurrent sessions
- No resource conflicts or race conditions

## 2. Results Aggregation Chain

### Scenario: Multi-Service Results Aggregation
**Test Method:** `test_multi_service_results_aggregation`
**Preconditions:**
- Mock all analysis services (grammar, pronunciation, lexical, fluency)
- Valid submission with multiple questions
- Clean results store state

**Integration Flow:**
1. Trigger analysis for multiple questions
2. Complete services in various orders across questions
3. Verify results are aggregated correctly per question
4. Verify submission-level aggregation waits for all questions
5. Test final results compilation and storage

**Expected Assertions:**
- Individual question results aggregate correctly
- Submission-level aggregation waits for all questions
- Results maintain proper structure and metadata
- Aggregation handles varying completion orders
- Final results include all service outputs

### Scenario: Partial Results Handling
**Test Method:** `test_partial_results_handling`
**Preconditions:**
- Mock some analysis services to fail
- Valid submission data
- Clean results store state

**Integration Flow:**
1. Start analysis process for submission
2. Complete some services successfully
3. Simulate failures in other services
4. Verify partial results are preserved
5. Test graceful degradation of final results

**Expected Assertions:**
- Successful service results are preserved
- Failed services don't corrupt successful results
- Partial aggregation maintains data integrity
- Final results indicate which services completed
- System continues processing despite partial failures

### Scenario: Cross-Question Results Coordination
**Test Method:** `test_cross_question_results_coordination`
**Preconditions:**
- Multiple questions in single submission
- Mock analysis services with different completion times
- Clean results store state

**Integration Flow:**
1. Start analysis for multiple questions simultaneously
2. Complete questions in different orders
3. Verify question-level isolation
4. Test submission-level coordination
5. Verify final submission results compilation

**Expected Assertions:**
- Questions process independently without interference
- Submission completion waits for all questions
- Results maintain question-specific isolation
- Cross-question coordination works correctly
- Final submission includes all question results

## 3. Analysis Service Coordination

### Scenario: Phase-Based Analysis Coordination
**Test Method:** `test_phase_based_analysis_coordination`
**Preconditions:**
- Mock all analysis services
- Valid audio and transcript data
- Clean coordination state

**Integration Flow:**
1. Trigger Phase 1 analysis (grammar, pronunciation, lexical)
2. Verify Phase 2 (fluency) waits for pronunciation completion
3. Test service dependency coordination
4. Verify all phases complete in correct order

**Expected Assertions:**
- Phase 1 services start simultaneously
- Phase 2 waits for pronunciation service completion
- Service dependencies are respected
- Coordination handles phase transitions correctly
- All services complete with proper sequencing

### Scenario: Service Failure Recovery in Coordination
**Test Method:** `test_service_failure_recovery_coordination`
**Preconditions:**
- Mock some analysis services to fail
- Valid analysis data
- Clean coordination state

**Integration Flow:**
1. Start analysis coordination
2. Simulate failure in Phase 1 service
3. Verify other services continue processing
4. Test recovery mechanisms
5. Verify final coordination with partial results

**Expected Assertions:**
- Service failures don't stop other services
- Coordination continues with available services
- Failed services are properly marked and handled
- Recovery mechanisms maintain system stability
- Final results reflect actual service completions

### Scenario: Service Timeout Handling
**Test Method:** `test_service_timeout_handling`
**Preconditions:**
- Mock analysis services with delays
- Timeout configurations
- Clean coordination state

**Integration Flow:**
1. Start analysis coordination
2. Simulate service timeouts
3. Verify timeout handling mechanisms
4. Test coordination with timed-out services
5. Verify cleanup and final results

**Expected Assertions:**
- Timeout mechanisms trigger correctly
- Timed-out services don't block coordination
- Cleanup occurs for timed-out operations
- Final results handle timeout scenarios
- System remains stable after timeouts

## 4. End-to-End Service Chain Integration

### Scenario: Complete Submission Processing Chain
**Test Method:** `test_complete_submission_processing_chain`
**Preconditions:**
- Real audio URLs and transcript data
- Mock external APIs to avoid costs
- Clean system state

**Integration Flow:**
1. Audio processing → file creation and registration
2. Transcription processing → text extraction
3. Analysis coordination → all 4 services
4. Results aggregation → question and submission level
5. Final storage and cleanup

**Expected Assertions:**
- Complete chain processes without errors
- All integration points work correctly
- File lifecycle managed properly throughout
- Results flow correctly between stages
- Final cleanup completes successfully

### Scenario: Multi-Submission Concurrent Processing
**Test Method:** `test_multi_submission_concurrent_processing`
**Preconditions:**
- Multiple submissions with different data
- Mock external services
- Clean system state

**Integration Flow:**
1. Start processing multiple submissions concurrently
2. Verify isolation between submissions
3. Test resource sharing and coordination
4. Verify independent completion
5. Test cleanup coordination

**Expected Assertions:**
- Submissions process independently
- No cross-contamination between submissions
- Resource sharing works correctly
- Concurrent completion handling works
- Cleanup coordination handles multiple submissions

## Integration Points Verified

1. **Service Chain Coordination**
   - AudioService → FileManager → AnalysisServices integration
   - File lifecycle management across service boundaries
   - Service dependency resolution and coordination

2. **Results Flow Management**
   - Results aggregation across multiple services
   - Question-level and submission-level coordination
   - Partial results handling and graceful degradation

3. **Resource Management**
   - File creation, tracking, and cleanup coordination
   - Concurrent session management
   - Resource sharing and isolation

4. **Error Resilience**
   - Service failure handling and recovery
   - Timeout management and cleanup
   - Partial completion scenarios

## Test Coverage Summary

The service chain testing covers:
- ✅ Core file lifecycle chain (AudioService → FileManager → AnalysisServices)
- ✅ Multi-service coordination and dependency management
- ✅ Results aggregation across services and questions
- ✅ Error handling and recovery in service chains
- ✅ Concurrent processing and resource management
- ✅ Phase-based analysis coordination
- ✅ Timeout handling and cleanup mechanisms
- ✅ End-to-end submission processing chains
- ❌ Performance testing under load (not implemented)
- ❌ Memory usage optimization testing (not implemented)
- ❌ Service chain monitoring and metrics (not implemented) 