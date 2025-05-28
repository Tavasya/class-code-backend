# Pub/Sub Message Integration Tests

This directory contains integration tests for **Pub/Sub Message Integration** - testing how webhook handlers process Pub/Sub push messages and coordinate service workflows, focusing on message-driven coordination rather than direct service calls.

## Test Philosophy

These tests focus on **message processing and coordination** by:
- ✅ Using real webhook handler instances (minimal mocking)
- ✅ Testing message parsing, routing, and coordination logic
- ✅ Verifying state management across async message flows
- ✅ Testing error recovery in message processing
- ✅ Using mocked analysis services to eliminate external API costs (80% of tests)
- ✅ Limited real API calls only for critical error scenarios

## Test Structure & Cost Breakdown

### 🔧 `conftest.py`
- Shared fixtures for all Pub/Sub message tests
- Mock analysis services fixture (`mock_all_analysis_services`)
- Sample Pub/Sub message factory (`sample_pubsub_messages`)
- Webhook request factory for creating FastAPI Request mocks
- Real webhook handler instances

### 📨 `test_message_parsing.py` - **Cost: $0.00**
**Tests: Base64 decoding, JSON extraction, message validation**
- Valid Pub/Sub push message parsing
- Malformed message handling (invalid base64, invalid JSON)
- Missing required fields error handling
- Message attributes and metadata extraction
- Unicode content and large message parsing

**Key Integration Points Tested:**
- `parse_pubsub_message()` utility function reliability
- Pub/Sub protocol compliance and format validation
- Error boundaries for malformed webhook requests

### 🔄 `test_webhook_coordination.py` - **Cost: $0.00**
**Tests: Service orchestration logic with mocked analysis services**
- Audio + Transcription coordination (AnalysisCoordinator logic)
- Parallel analysis completion coordination (AnalysisWebhook state management)
- Submission-level aggregation across multiple questions
- State isolation between different submissions
- Out-of-order message handling

**Key Integration Points Tested:**
- AnalysisCoordinator waits for both audio AND transcription completion
- AnalysisWebhook tracks completion of all 4 analysis services
- Submission completion triggers only after all questions complete
- Cross-submission state isolation (no interference)

### ⚡ `test_message_ordering.py` - **Cost: $0.00**
**Tests: Async message sequencing and state management**
- Out-of-order audio/transcription processing
- Analysis completion in unusual order (lexical → pronunciation → fluency → grammar)
- Question dependency ordering for submission completion
- Interleaved processing of multiple submissions
- State persistence through message delays

**Key Integration Points Tested:**
- Coordination waits correctly regardless of message arrival order
- State management persists across async operations
- Multiple submissions process independently without race conditions
- Partial completion doesn't block other processing

### 🚨 `test_error_recovery.py` - **Cost: $2-5**
**Tests: Error recovery with limited real API calls**
- Webhook parsing error recovery (malformed messages) - **$0.00**
- Missing required fields handling - **$0.00**
- Analysis service failure with real API (1 failing call) - **~$0.80**
- Partial analysis failure handling - **$0.00**
- Database storage failure recovery - **$0.00**
- Concurrent error isolation - **$0.00**
- Timeout simulation and recovery - **$0.00**

**Key Integration Points Tested:**
- System resilience to invalid messages
- Graceful degradation when services fail
- Error isolation (failure in one submission doesn't affect others)
- Memory leak prevention with failed submissions

## Key Differences from Other Testing

### vs. Service Chain Integration (existing)
| **Pub/Sub Message Integration** | **Service Chain Integration** |
|--------------------------------|------------------------------|
| Tests message-driven coordination | Tests direct service calls |
| Webhook processing pipelines | Service method interfaces |
| Message parsing and routing | Business logic coordination |
| State management across messages | Service state management |

### vs. External API Integration (existing)
| **Pub/Sub Message Integration** | **External API Integration** |
|--------------------------------|------------------------------|
| Tests webhook message handling | Tests external service reliability |
| Mock expensive services (80% of tests) | Real API calls for integration |
| Message format validation | API response validation |
| Error recovery in message processing | Error recovery in API calls |

## Running Tests

### Run all Pub/Sub message tests:
```bash
pytest tests/int_testing/pubsub_message_testing/ -v
```

### Run by cost category:
```bash
# Free tests only (message parsing + coordination)
pytest tests/int_testing/pubsub_message_testing/test_message_parsing.py -v
pytest tests/int_testing/pubsub_message_testing/test_webhook_coordination.py -v  
pytest tests/int_testing/pubsub_message_testing/test_message_ordering.py -v

# Low-cost error recovery tests
pytest tests/int_testing/pubsub_message_testing/test_error_recovery.py -v
```

### Run specific test categories:
```bash
# Message format validation
pytest tests/int_testing/pubsub_message_testing/ -v -k "parsing"

# Coordination logic
pytest tests/int_testing/pubsub_message_testing/ -v -k "coordination"

# Error scenarios  
pytest tests/int_testing/pubsub_message_testing/ -v -k "error"
```

## Critical Message Flows Covered

### 📨 **Flow 1: Message Parsing Pipeline**
```
Pub/Sub Push Message → FastAPI Request → parse_pubsub_message()
  ↓ (Base64 decode)
JSON Data Extraction → Message Validation
  ↓ (error handling)
Webhook Handler Processing
```

### 🔄 **Flow 2: Audio + Transcription Coordination**
```
AUDIO_CONVERSION_DONE webhook (parallel)
TRANSCRIPTION_DONE webhook (parallel)
  ↓ (coordination logic)
AnalysisCoordinator.handle_audio_done()
AnalysisCoordinator.handle_transcription_done()
  ↓ (both complete)
QUESTION_ANALYSIS_READY message published
```

### ⚡ **Flow 3: Parallel Analysis Coordination**
```
QUESTION_ANALYSIS_READY webhook
  ↓ (Phase 1: parallel)
Grammar + Pronunciation + Lexical services triggered
  ↓ (Phase 2: pronunciation → fluency)
PRONUNCIATION_DONE → Fluency service triggered
  ↓ (all complete)
ANALYSIS_COMPLETE message published
```

### 🏁 **Flow 4: Submission Completion**
```
ANALYSIS_COMPLETE webhook (for each question)
  ↓ (aggregation logic)
AnalysisWebhook submission state tracking
  ↓ (all questions complete)
SUBMISSION_ANALYSIS_COMPLETE message published
  ↓ (storage)
ResultsStore + DatabaseService updates
```

## Cost Management Strategy

### **Tiered Testing Approach**
```
Tier 1: Message Logic ($0.00/run)
├── Message parsing and validation
├── Coordination state management  
└── Message ordering scenarios

Tier 2: Error Recovery ($2-5/run)
├── 1-2 real API calls for realistic failures
├── Database failure simulation
└── Timeout and recovery testing
```

### **Mock vs Real Strategy**
```
Mocked (80% of tests):
├── Analysis services (pronunciation, grammar, lexical, fluency)
├── Database operations (most tests)
└── PubSub publishing

Real (20% of tests):
├── Webhook handler processing logic
├── Message parsing utilities
├── State management coordination
└── Limited real API calls for error scenarios
```

## Dependencies

### Webhook Handlers
- **AnalysisWebhook**: Core analysis coordination and state management
- **SubmissionWebhook**: Student submission processing
- **AudioWebhook**: Audio conversion message handling  
- **TranscriptionWebhook**: Transcription completion handling

### External Services (Mocked in most tests)
- **PronunciationService**: Azure Speech API (mocked except error tests)
- **GrammarService**: OpenAI API (mocked except error tests)
- **LexicalService**: OpenAI API (mocked except error tests)
- **DatabaseService**: Supabase operations (mocked except storage tests)

### Python Packages
- `pytest-asyncio`: Async test support
- `unittest.mock`: Comprehensive mocking for cost control
- `fastapi`: Request mocking for webhook testing

## Mocking Strategy

### What IS Mocked ❌
- `PubSubClient.publish_message_by_name()` - Prevents actual message publishing
- Analysis services (80% of tests) - Eliminates external API costs
- `DatabaseService.update_submission_results()` - Prevents database writes in most tests

### What is NOT Mocked ✅
- Webhook handler business logic - tests real coordination
- Message parsing utilities - tests real Pub/Sub compliance
- State management across webhook calls - tests real coordination bugs
- `ResultsStore` operations - tests real memory cache behavior

## Success Criteria

These tests catch critical message processing bugs:
- ✅ **Message routing failures** (webhook misconfiguration, format changes)
- ✅ **State coordination errors** (race conditions, out-of-order handling)
- ✅ **Message parsing failures** (Pub/Sub protocol compliance)
- ✅ **Error recovery gaps** (system crashes on invalid messages)
- ✅ **Memory leaks** (incomplete state cleanup)

## Cost-Benefit Analysis

**Total Cost:** $2-5 per complete test run
**Cost Breakdown:**
- Message parsing: $0.00 (pure logic)
- Webhook coordination: $0.00 (mocked services)
- Message ordering: $0.00 (mocked services)  
- Error recovery: $2-5 (1-2 real API calls)

**Value:** Prevents message processing outages that could cost $100s-1000s in production downtime and data corruption.

## Troubleshooting

### Common Issues

**Tests failing with "HTTPException":**
- Check message format in `sample_pubsub_messages` fixture
- Verify Base64 encoding is correct in test data

**Coordination tests timing out:**
- Check that `mock_pubsub_client` is being used correctly
- Verify state management assertions are reasonable

**Error recovery tests expensive:**
- Ensure mocking is applied correctly to limit real API calls
- Check that only designated error tests use real services

**Memory leaks in test state:**
- Use `results_store_cleanup` fixture consistently
- Clear webhook state between tests if needed 