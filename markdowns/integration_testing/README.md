# Integration Testing Documentation

This directory contains comprehensive documentation for all integration testing components in the backend system. Each document follows a consistent structure based on the API testing markdown format, providing detailed test scenarios, integration flows, and coverage analysis.

## Test Documentation Overview

### 📨 [Pub/Sub Message Testing](./pubsub_message_testing.md)
**Focus:** Message coordination, ordering, and state management
- Message sequencing and out-of-order processing
- Webhook coordination across handlers
- State persistence and recovery mechanisms
- Error handling and resilience testing
- Multi-submission isolation and processing

**Key Integration Points:**
- Pub/Sub message routing between services
- Results store persistence across async operations
- Cross-service message dependencies and ordering

### 🔗 [Service Chain Testing](./service_chain_testing.md)
**Focus:** Service coordination and file lifecycle management
- Core file lifecycle chain (AudioService → FileManager → AnalysisServices)
- Multi-service coordination and dependency management
- Results aggregation across services and questions
- Phase-based analysis coordination
- Concurrent processing and resource management

**Key Integration Points:**
- Service chain coordination and dependency resolution
- File lifecycle management across service boundaries
- Results flow management and aggregation

### 📁 [File Management Testing](./file_management_testing.md)
**Focus:** File operations, storage, and lifecycle management
- Complete file lifecycle management and session tracking
- Supabase storage integration (upload, download, cleanup)
- Audio format conversion and quality preservation
- Concurrent session management and isolation
- End-to-end file management workflows

**Key Integration Points:**
- File lifecycle management and session coordination
- Storage integration with external services
- Format processing and download management

### 🌐 [External API Testing](./external_api_testing.md)
**Focus:** Third-party API integration and coordination
- OpenAI integration for grammar and lexical analysis
- Azure Speech integration for pronunciation analysis
- AssemblyAI integration for transcription services
- Multi-API workflow coordination
- API authentication and error handling

**Key Integration Points:**
- API communication and authentication mechanisms
- Data format integration and schema compliance
- Service coordination across multiple external APIs

## Integration Testing Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Integration Test Layers                  │
├─────────────────────────────────────────────────────────────┤
│  External APIs     │ OpenAI │ Azure Speech │ AssemblyAI    │
├─────────────────────────────────────────────────────────────┤
│  Service Chain     │ Audio → File Manager → Analysis       │
├─────────────────────────────────────────────────────────────┤
│  Message Flow      │ Pub/Sub → Webhooks → State Management │
├─────────────────────────────────────────────────────────────┤
│  File Management   │ Storage → Conversion → Lifecycle      │
└─────────────────────────────────────────────────────────────┘
```

## Test Categories and Scope

### 🔄 **Message Flow Integration**
- **Pub/Sub Message Testing**: Async message coordination and state management
- **Webhook Coordination**: Cross-handler communication and data flow
- **State Persistence**: Results store management and recovery

### ⚙️ **Service Integration**
- **Service Chain Testing**: Multi-service workflows and dependencies
- **Analysis Coordination**: Phase-based processing and aggregation
- **Resource Management**: File lifecycle and cleanup coordination

### 💾 **Data Integration**
- **File Management Testing**: Storage, conversion, and lifecycle management
- **Format Processing**: Audio conversion and quality preservation
- **Storage Integration**: Supabase operations and error handling

### 🌍 **External Integration**
- **External API Testing**: Third-party service integration
- **Authentication**: API key management and validation
- **Error Resilience**: Failure handling and recovery mechanisms

## Common Integration Patterns

### 1. **Async Coordination Pattern**
Used across all integration tests for managing asynchronous operations:
- Message ordering and sequencing
- Service completion tracking
- State persistence across async boundaries

### 2. **Resource Lifecycle Pattern**
Consistent approach to resource management:
- Creation and registration
- Dependency tracking
- Automatic cleanup and coordination

### 3. **Error Resilience Pattern**
Standardized error handling across integrations:
- Graceful degradation
- Partial failure recovery
- System stability maintenance

### 4. **Isolation Pattern**
Ensuring proper isolation between concurrent operations:
- Session-based isolation
- Submission-level separation
- Resource sharing without interference

## Test Execution Guidelines

### Prerequisites
- All integration tests require proper environment setup
- External API tests need valid API keys (skipped if unavailable)
- File management tests use temporary directories for isolation
- Service chain tests mock external dependencies to avoid costs

### Running Integration Tests
```bash
# Run all integration tests
pytest tests/int_testing/

# Run specific integration test category
pytest tests/int_testing/pubsub_message_testing/
pytest tests/int_testing/service_chain_testing/
pytest tests/int_testing/file_management_testing/
pytest tests/int_testing/externalAPI_testing/

# Run with API key validation (external APIs)
OPENAI_API_KEY=your_key AZURE_SPEECH_KEY=your_key pytest tests/int_testing/externalAPI_testing/
```

### Test Configuration
- **Async Tests**: All integration tests use `@pytest.mark.asyncio`
- **Mocking Strategy**: External dependencies mocked to avoid costs
- **Cleanup**: Automatic cleanup of test resources and temporary files
- **Isolation**: Each test runs in isolated environment

## Coverage Analysis

### ✅ **Well Covered Areas**
- Message coordination and state management
- Service chain integration and file lifecycle
- Error handling and recovery mechanisms
- Concurrent processing and resource management
- External API integration and authentication

### ⚠️ **Areas for Enhancement**
- Performance testing under load
- Memory usage optimization
- Network failure simulation
- Cost optimization for external APIs
- Monitoring and metrics integration

## Integration Test Maintenance

### Adding New Integration Tests
1. Follow the established markdown documentation format
2. Use consistent test patterns and fixtures
3. Include proper cleanup and error handling
4. Document integration points and dependencies
5. Update this README with new test categories

### Updating Existing Tests
1. Maintain backward compatibility where possible
2. Update documentation to reflect changes
3. Ensure test isolation and cleanup still work
4. Verify integration points remain valid
5. Update coverage analysis as needed

## Related Documentation
- [API Testing Documentation](../api_testing/) - Individual endpoint testing
- [Test Configuration](../../tests/int_testing/conftest.py) - Shared fixtures and utilities
- [Service Documentation](../../app/services/) - Service implementation details
- [Webhook Documentation](../../app/webhooks/) - Webhook handler implementations

---

*This documentation provides comprehensive coverage of integration testing scenarios, ensuring reliable system behavior across all service boundaries and external dependencies.* 