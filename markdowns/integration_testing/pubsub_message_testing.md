# Pub/Sub Message Testing Integration Test Plan

## Files to Reference
- `tests/int_testing/pubsub_message_testing/test_message_ordering.py` - Message sequencing and state management tests
- `tests/int_testing/pubsub_message_testing/test_error_recovery.py` - Error handling and recovery tests
- `tests/int_testing/pubsub_message_testing/test_webhook_coordination.py` - Webhook coordination tests
- `tests/int_testing/pubsub_message_testing/test_message_parsing.py` - Message parsing and validation tests
- `tests/int_testing/pubsub_message_testing/conftest.py` - Test fixtures and utilities
- `app/webhooks/analysis_webhook.py` - Webhook handlers for analysis coordination

## Test Setup
- Uses `AsyncMock` for mocking Pub/Sub clients and external services
- Uses `webhook_request_factory` for creating webhook request objects
- Uses `create_base64_message` utility for encoding Pub/Sub message data
- Tests use `results_store_cleanup` fixture for state management
- All tests are async and use `@pytest.mark.asyncio`

## 1. Message Ordering and Sequencing

### Scenario: Out-of-Order Audio Transcription Processing
**Test Method:** `test_out_of_order_audio_transcription_processing`
**Preconditions:**
- Mock Pub/Sub client with `AsyncMock`
- Clean results store state
- Valid submission URL and question data

**Integration Flow:**
1. Send TRANSCRIPTION message first (unusual order)
2. Verify analysis is NOT triggered yet (waiting for audio)
3. Send AUDIO message second (completes the pair)
4. Verify analysis is NOW triggered with combined data

**Expected Assertions:**
- First message: No Pub/Sub publish calls (waiting state)
- Second message: Exactly 1 publish call to "QUESTION_ANALYSIS_READY"
- Published message contains data from both transcription and audio
- Proper coordination between webhook handlers

### Scenario: Analysis Completion Out of Order
**Test Method:** `test_analysis_completion_out_of_order`
**Preconditions:**
- Mock all analysis services (grammar, pronunciation, lexical, fluency)
- Clean results store state
- Valid analysis ready data

**Integration Flow:**
1. Trigger analysis with "QUESTION_ANALYSIS_READY" message
2. Complete LEXICAL first (unusual order)
3. Complete PRONUNCIATION second (triggers fluency in Phase 2)
4. Complete FLUENCY third
5. Complete GRAMMAR last

**Expected Assertions:**
- Analysis waits for all 4 services regardless of completion order
- No "ANALYSIS_COMPLETE" message until all services finish
- Final completion triggers proper aggregation
- State management handles out-of-order completion correctly

### Scenario: Question Dependency Ordering for Submission Completion
**Test Method:** `test_question_dependency_ordering_submission_completion`
**Preconditions:**
- Mock database service for submission updates
- Multiple questions in submission (total_questions > 1)
- Clean results store state

**Integration Flow:**
1. Complete analysis for question 2 first
2. Verify submission is NOT marked complete (waiting for question 1)
3. Complete analysis for question 1 second
4. Verify submission is NOW marked complete

**Expected Assertions:**
- Submission completion waits for all questions
- Database update only called when all questions complete
- Proper dependency tracking across questions
- Correct submission status management

## 2. Mixed Submission Processing

### Scenario: Interleaved Processing of Multiple Submissions
**Test Method:** `test_mixed_submission_interleaved_processing`
**Preconditions:**
- Mock all analysis services
- Multiple submissions with different IDs
- Clean results store state

**Integration Flow:**
1. Start analysis for submission A, question 1
2. Start analysis for submission B, question 1
3. Complete services for submission A in mixed order
4. Complete services for submission B in different order
5. Verify both submissions complete independently

**Expected Assertions:**
- Submissions process independently without interference
- State isolation between different submission URLs
- Proper completion tracking per submission
- No cross-contamination of results

## 3. State Persistence and Recovery

### Scenario: Delayed Message Processing with State Persistence
**Test Method:** `test_delayed_message_processing_with_state_persistence`
**Preconditions:**
- Mock analysis services with delays
- Valid submission data
- Clean results store state

**Integration Flow:**
1. Send analysis ready message
2. Complete some services immediately
3. Simulate delay before completing remaining services
4. Verify state persists across delays
5. Complete remaining services and verify final result

**Expected Assertions:**
- State persists during processing delays
- Partial completion tracking works correctly
- Final aggregation includes all delayed results
- No data loss during extended processing

### Scenario: Rapid Sequential Message Processing
**Test Method:** `test_rapid_sequential_message_processing`
**Preconditions:**
- Mock analysis services for fast responses
- Multiple rapid messages
- Clean results store state

**Integration Flow:**
1. Send multiple messages in rapid succession
2. Verify all messages are processed correctly
3. Check for race conditions in state management
4. Ensure proper sequencing despite rapid timing

**Expected Assertions:**
- All rapid messages processed successfully
- No race conditions in state updates
- Proper message ordering maintained
- Concurrent processing handled correctly

## 4. Error Recovery and Resilience

### Scenario: Partial Completion with Missing Messages
**Test Method:** `test_partial_completion_ordering_with_missing_messages`
**Preconditions:**
- Mock analysis services with some failures
- Valid submission data
- Clean results store state

**Integration Flow:**
1. Start analysis process
2. Complete some services successfully
3. Simulate missing/failed messages for other services
4. Verify graceful handling of partial completion
5. Test timeout and cleanup mechanisms

**Expected Assertions:**
- System handles missing messages gracefully
- Partial results are preserved
- Timeout mechanisms work correctly
- Cleanup occurs for incomplete sessions

## 5. Webhook Coordination

### Scenario: Multi-Webhook Message Coordination
**Test Method:** `test_webhook_coordination_across_handlers`
**Preconditions:**
- Multiple webhook handlers (transcription, audio, analysis)
- Mock Pub/Sub coordination
- Clean results store state

**Integration Flow:**
1. Send messages to different webhook handlers
2. Verify cross-handler coordination
3. Test message routing and processing
4. Ensure proper handler isolation

**Expected Assertions:**
- Messages route to correct handlers
- Cross-handler state sharing works
- Proper isolation between handler types
- Coordination messages flow correctly

## 6. Message Parsing and Validation

### Scenario: Base64 Message Decoding and JSON Parsing
**Test Method:** `test_message_parsing_validation`
**Preconditions:**
- Various message formats (valid and invalid)
- Mock webhook handlers
- Clean application state

**Integration Flow:**
1. Send valid base64 encoded JSON messages
2. Send invalid base64 data
3. Send valid base64 with invalid JSON
4. Send malformed message structures
5. Verify proper parsing and error handling

**Expected Assertions:**
- Valid messages parse correctly
- Invalid base64 handled gracefully with error responses
- Invalid JSON handled gracefully with error responses
- Malformed structures rejected appropriately
- Error messages are informative and consistent

## Integration Points Verified

1. **Message Flow Coordination**
   - Pub/Sub message routing between services
   - Webhook handler coordination and state sharing
   - Cross-service message dependencies and ordering

2. **State Management**
   - Results store persistence across async operations
   - State isolation between different submissions
   - Cleanup and timeout handling for incomplete sessions

3. **Error Resilience**
   - Graceful handling of out-of-order messages
   - Recovery from partial failures and missing messages
   - Proper error propagation and logging

4. **Performance and Concurrency**
   - Concurrent message processing without interference
   - Rapid sequential message handling
   - Resource cleanup and memory management

## Test Coverage Summary

The Pub/Sub message testing covers:
- ✅ Message ordering and sequencing scenarios
- ✅ Out-of-order processing and coordination
- ✅ Multi-submission isolation and processing
- ✅ State persistence and recovery mechanisms
- ✅ Error handling and resilience testing
- ✅ Webhook coordination across handlers
- ✅ Message parsing and validation
- ✅ Concurrent and rapid processing scenarios
- ❌ Load testing with high message volumes (not implemented)
- ❌ Network failure simulation (not implemented)
- ❌ Message deduplication testing (not implemented) 