# Testing Structure and Strategies

## 🧪 Overview

The Audio Analysis API includes comprehensive testing infrastructure organized into different testing categories to ensure system reliability and correctness.

## 📁 Test Organization

**Base Directory**: `tests/`

### Test Categories:

1. **API Testing** (`tests/api_testing/`)
   - Endpoint functionality testing
   - Request/response validation
   - Authentication and authorization tests

2. **Integration Testing** (`tests/int_testing/`)
   - End-to-end workflow testing
   - Service interaction validation
   - External API integration tests

## 🔍 Integration Testing Structure

### External API Testing
**Directory**: `tests/int_testing/externalAPI_testing/`

**Purpose**: Validate integration with external services
- **OpenAI API** integration tests
- **Azure Speech Services** connectivity
- **AssemblyAI** transcription testing  
- **Supabase** database operations
- **Google Cloud Pub/Sub** messaging

**Test Categories**:
```python
# Example test structure
class TestOpenAIIntegration:
    def test_grammar_analysis_api_call()
    def test_api_key_validation()
    def test_rate_limiting_handling()
    def test_error_response_handling()

class TestAzureSpeechServices:
    def test_speech_to_text_conversion()
    def test_audio_format_support()
    def test_language_detection()
    def test_authentication_failure()
```

### File Management Testing
**Directory**: `tests/int_testing/file_management_testing/`

**Purpose**: Validate file lifecycle and cleanup operations
- **Temporary file creation** and cleanup
- **Session-based file management**
- **Storage quota enforcement**
- **File permission handling**
- **Concurrent file access**

**Test Scenarios**:
```python
class TestFileManager:
    def test_session_file_creation()
    def test_periodic_cleanup_task()
    def test_file_access_permissions()
    def test_storage_limit_enforcement()
    def test_concurrent_file_operations()
```

### Pub/Sub Message Testing
**Directory**: `tests/int_testing/pubsub_message_testing/`

**Purpose**: Validate message-driven architecture
- **Message publishing** and consumption
- **Topic and subscription** management
- **Message ordering** and delivery guarantees
- **Error handling** and retry logic
- **Dead letter queue** functionality

**Message Flow Tests**:
```python
class TestPubSubFlow:
    def test_student_submission_flow()
    def test_audio_conversion_messaging()
    def test_transcription_done_notification()
    def test_analysis_coordination_messages()
    def test_final_result_aggregation()
    
class TestMessageReliability:
    def test_message_persistence()
    def test_retry_on_failure()
    def test_duplicate_message_handling()
    def test_dead_letter_queue_routing()
```

### Service Chain Testing
**Directory**: `tests/int_testing/service_chain_testing/`

**Purpose**: Validate end-to-end service interactions
- **Complete analysis pipeline** testing
- **Service dependency** validation
- **Error propagation** handling
- **Performance benchmarking**
- **Scalability testing**

**Chain Test Examples**:
```python
class TestAnalysisChain:
    def test_complete_audio_analysis_pipeline()
    def test_partial_service_failure_handling()
    def test_service_timeout_recovery()
    def test_concurrent_submission_processing()
    
class TestServiceDependencies:
    def test_audio_transcription_coordination()
    def test_analysis_service_independence()
    def test_database_service_integration()
    def test_webhook_delivery_chain()
```

## 🎯 Testing Strategies

### 1. **Unit Testing Strategy**
**Focus**: Individual service and function testing

```python
# Example unit test structure
class TestPronunciationService:
    def test_phoneme_analysis()
    def test_word_scoring_algorithm()
    def test_confidence_calculation()
    def test_error_handling()

class TestDatabaseService:
    def test_result_storage()
    def test_data_validation()
    def test_query_operations()
    def test_connection_handling()
```

### 2. **Integration Testing Strategy**
**Focus**: Service-to-service communication

```python
class TestServiceIntegration:
    def test_audio_service_to_coordinator()
    def test_coordinator_to_analysis_services()
    def test_analysis_to_database_flow()
    def test_database_to_webhook_notification()
```

### 3. **End-to-End Testing Strategy**
**Focus**: Complete user workflows

```python
class TestE2EWorkflows:
    def test_single_audio_submission()
    def test_multiple_audio_batch_submission()
    def test_error_recovery_scenarios()
    def test_performance_under_load()
```

## 🔧 Test Configuration

### Test Environment Setup
```python
# conftest.py example
@pytest.fixture(scope="session")
def test_app():
    """Create test FastAPI application"""
    app = create_test_app()
    return app

@pytest.fixture
def test_client(test_app):
    """Create test client"""
    return TestClient(test_app)

@pytest.fixture
def mock_external_apis():
    """Mock external API responses"""
    with patch('app.services.openai_client') as mock_openai:
        with patch('app.services.azure_client') as mock_azure:
            yield {
                'openai': mock_openai,
                'azure': mock_azure
            }
```

### Test Data Management
```python
# Test data fixtures
@pytest.fixture
def sample_audio_data():
    return {
        'audio_url': 'https://example.com/test_audio.mp3',
        'question_number': 1,
        'submission_url': 'https://test.com/submission/123'
    }

@pytest.fixture
def sample_transcription():
    return "This is a sample transcription for testing purposes."

@pytest.fixture
def expected_analysis_result():
    return {
        'overall_score': 85.5,
        'pronunciation': {...},
        'fluency': {...},
        'grammar': {...}
    }
```

## 📊 Test Coverage Strategy

### Coverage Targets
- **Unit Tests**: 90%+ coverage for service logic
- **Integration Tests**: 80%+ coverage for API endpoints
- **E2E Tests**: 70%+ coverage for critical user flows

### Coverage Areas
```python
# Critical areas requiring high coverage
CRITICAL_COVERAGE_AREAS = [
    'app/services/',           # Business logic
    'app/api/v1/endpoints/',   # API endpoints
    'app/models/',             # Data validation
    'app/core/',               # Configuration
    'app/pubsub/'              # Messaging
]
```

## 🚀 Performance Testing

### Load Testing Scenarios
```python
class TestPerformance:
    def test_concurrent_submissions(self):
        """Test handling 100 concurrent submissions"""
        pass
    
    def test_memory_usage_under_load(self):
        """Monitor memory consumption during processing"""
        pass
    
    def test_response_time_benchmarks(self):
        """Ensure response times within SLA"""
        pass
```

### Benchmark Targets
- **API Response Time**: < 200ms for synchronous endpoints
- **Analysis Processing**: < 30 seconds per audio file
- **Memory Usage**: < 2GB per service instance
- **Concurrent Users**: Support 50+ simultaneous submissions

## 🔍 Test Automation

### CI/CD Integration
```yaml
# GitHub Actions test workflow
name: Test Suite
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run unit tests
        run: pytest tests/ -v --cov=app
      - name: Run integration tests
        run: pytest tests/int_testing/ -v
      - name: Generate coverage report
        run: coverage xml
```

### Test Data Management
- **Synthetic audio files** for testing
- **Mock API responses** for external services
- **Test database** with isolated data
- **Cleanup procedures** for test artifacts

## 🛠️ Testing Tools and Frameworks

### Primary Testing Stack
- **pytest**: Main testing framework
- **pytest-asyncio**: Async test support
- **pytest-cov**: Coverage reporting
- **pytest-mock**: Mocking utilities
- **httpx**: HTTP client testing

### Additional Tools
- **Factory Boy**: Test data generation
- **Faker**: Synthetic data creation
- **pytest-benchmark**: Performance testing
- **pytest-xdist**: Parallel test execution

### Mock and Fixture Examples
```python
# Service mocking
@pytest.fixture
def mock_pronunciation_service():
    with patch('app.services.pronunciation_service.PronunciationService') as mock:
        mock.return_value.analyze.return_value = {
            'overall_score': 85.0,
            'confidence': 0.92
        }
        yield mock

# Database mocking
@pytest.fixture
def mock_database():
    with patch('app.core.config.supabase') as mock_db:
        mock_db.table.return_value.insert.return_value.execute.return_value = {'data': []}
        yield mock_db
```

## 📝 Test Documentation

### Test Case Documentation
```python
def test_audio_conversion_success():
    """
    Test Case: Audio Conversion Success
    
    Given: Valid audio URL and metadata
    When: Audio conversion service is called
    Then: WAV file is created and metadata is correct
    
    Acceptance Criteria:
    - Audio file is downloaded successfully
    - Conversion to WAV format completes
    - Metadata includes correct file paths
    - Session ID is assigned for cleanup
    """
    pass
```

### Test Reporting
- **Coverage reports** with detailed breakdowns
- **Performance benchmarks** with trend analysis
- **Integration test results** with service health
- **Error tracking** and failure analysis

## 🔄 Continuous Testing Strategy

### Development Workflow
1. **Local Testing**: Developer runs tests before commit
2. **Pre-commit Hooks**: Automated test execution
3. **CI Pipeline**: Full test suite on push
4. **Staging Tests**: Integration tests on staging environment
5. **Production Monitoring**: Health checks and metrics

### Test Maintenance
- **Regular test data updates**
- **Mock service response updates**
- **Performance baseline adjustments**
- **Test case reviews** and improvements 