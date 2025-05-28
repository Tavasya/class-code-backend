# External API Testing Integration Test Plan

## Files to Reference
- `tests/int_testing/externalAPI_testing/test_openai.py` - OpenAI API integration tests
- `tests/int_testing/externalAPI_testing/test_azure_speech.py` - Azure Speech API integration tests
- `tests/int_testing/externalAPI_testing/test_assemblyai.py` - AssemblyAI API integration tests
- `tests/int_testing/externalAPI_testing/conftest.py` - Test fixtures and utilities
- `app/services/grammar_service.py` - Grammar analysis service using OpenAI
- `app/services/lexical_service.py` - Lexical analysis service using OpenAI
- `app/services/pronunciation_service.py` - Pronunciation analysis service using Azure Speech
- `app/services/transcription_service.py` - Transcription service using AssemblyAI

## Test Setup
- Uses `skip_if_no_api_keys` fixture to skip tests when API keys unavailable
- Tests are designed to work with real external APIs when keys are provided
- Uses minimal API calls to avoid excessive costs during testing
- All tests are async and use `@pytest.mark.asyncio`
- Tests focus on integration verification rather than comprehensive functionality

## 1. OpenAI API Integration

### Scenario: Grammar Analysis Integration
**Test Method:** `test_grammar_analysis_works`
**Preconditions:**
- Valid OpenAI API key available
- Test text with grammatical errors
- Grammar service properly configured

**Integration Flow:**
1. Send text with known grammatical errors to OpenAI
2. Verify API response structure and content
3. Check grade calculation and issue detection
4. Validate response format matches expected schema

**Expected Assertions:**
- Response contains `"grade"` field with numeric value (0-100)
- Response contains `"issues"` field with list of detected problems
- Grade value is reasonable for the input text quality
- Issues list contains relevant grammatical feedback
- API integration completes without errors

### Scenario: Lexical Analysis Integration
**Test Method:** `test_lexical_analysis_works`
**Preconditions:**
- Valid OpenAI API key available
- Test sentences for vocabulary analysis
- Lexical service properly configured

**Integration Flow:**
1. Send sentences to OpenAI for lexical resource analysis
2. Verify API response structure and content
3. Check vocabulary complexity assessment
4. Validate response format matches expected schema

**Expected Assertions:**
- Response contains `"grade"` field with numeric value (0-100)
- Response contains `"issues"` field with vocabulary feedback
- Grade reflects vocabulary complexity appropriately
- Issues list provides relevant lexical insights
- API integration completes without errors

### Scenario: High-Quality Grammar Scoring
**Test Method:** `test_good_grammar_gets_high_score`
**Preconditions:**
- Valid OpenAI API key available
- Well-formed grammatically correct text
- Grammar service properly configured

**Integration Flow:**
1. Send grammatically correct text to OpenAI
2. Verify high score for good grammar
3. Check that issues list is minimal or empty
4. Validate scoring accuracy for quality text

**Expected Assertions:**
- Grade is 70 or higher for good grammar
- Issues list is empty or contains minor suggestions
- API correctly identifies high-quality grammar
- Scoring system works as expected
- Integration maintains consistency

### Scenario: Advanced Vocabulary Recognition
**Test Method:** `test_advanced_vocabulary_gets_high_score`
**Preconditions:**
- Valid OpenAI API key available
- Text with advanced vocabulary words
- Lexical service properly configured

**Integration Flow:**
1. Send text with sophisticated vocabulary to OpenAI
2. Verify high score for advanced word usage
3. Check recognition of complex vocabulary
4. Validate scoring reflects vocabulary sophistication

**Expected Assertions:**
- Grade is 85 or higher for advanced vocabulary
- API recognizes sophisticated word choices
- Scoring system rewards vocabulary complexity
- Integration accurately assesses lexical resources
- Response provides meaningful vocabulary feedback

## 2. Azure Speech API Integration

### Scenario: Pronunciation Analysis Integration
**Test Method:** `test_azure_pronunciation_analysis`
**Preconditions:**
- Valid Azure Speech API key available
- Test audio file for pronunciation analysis
- Reference text for comparison
- Pronunciation service properly configured

**Integration Flow:**
1. Send audio file and reference text to Azure Speech API
2. Verify pronunciation assessment response
3. Check accuracy scores and phoneme-level feedback
4. Validate response format and content structure

**Expected Assertions:**
- Response contains pronunciation accuracy scores
- Phoneme-level analysis provided where applicable
- Audio quality assessment included
- Response format matches Azure Speech API schema
- Integration completes without authentication errors

### Scenario: Audio Quality Assessment
**Test Method:** `test_azure_audio_quality_assessment`
**Preconditions:**
- Valid Azure Speech API key available
- Audio files with varying quality levels
- Pronunciation service properly configured

**Integration Flow:**
1. Send high-quality audio to Azure Speech API
2. Send low-quality audio to Azure Speech API
3. Compare quality assessments and scores
4. Verify API can distinguish audio quality differences

**Expected Assertions:**
- High-quality audio receives better scores
- Low-quality audio flagged appropriately
- Quality assessment reflects actual audio conditions
- API provides meaningful quality feedback
- Integration handles varying audio quality gracefully

### Scenario: Pronunciation Error Detection
**Test Method:** `test_azure_pronunciation_error_detection`
**Preconditions:**
- Valid Azure Speech API key available
- Audio with known pronunciation errors
- Correct reference text for comparison
- Pronunciation service properly configured

**Integration Flow:**
1. Send audio with mispronunciations to Azure Speech API
2. Verify error detection in pronunciation assessment
3. Check specific phoneme or word-level feedback
4. Validate error reporting accuracy

**Expected Assertions:**
- Pronunciation errors detected and reported
- Specific feedback provided for mispronounced elements
- Error severity reflected in scoring
- API provides actionable pronunciation feedback
- Integration accurately identifies pronunciation issues

## 3. AssemblyAI Integration

### Scenario: Audio Transcription Integration
**Test Method:** `test_assemblyai_transcription_works`
**Preconditions:**
- Valid AssemblyAI API key available
- Test audio file with clear speech
- Transcription service properly configured

**Integration Flow:**
1. Upload audio file to AssemblyAI for transcription
2. Poll for transcription completion
3. Retrieve transcription results
4. Verify transcription accuracy and format

**Expected Assertions:**
- Audio uploads successfully to AssemblyAI
- Transcription completes within reasonable time
- Transcribed text is reasonably accurate
- Response format matches AssemblyAI schema
- Integration handles async transcription process correctly

### Scenario: Transcription Quality Assessment
**Test Method:** `test_assemblyai_transcription_quality`
**Preconditions:**
- Valid AssemblyAI API key available
- High-quality audio with clear speech
- Known reference text for comparison
- Transcription service properly configured

**Integration Flow:**
1. Send high-quality audio to AssemblyAI
2. Compare transcription results with reference text
3. Assess transcription accuracy and completeness
4. Verify confidence scores and quality metrics

**Expected Assertions:**
- Transcription accuracy is high for clear audio
- Confidence scores reflect transcription quality
- Word-level timing information provided where available
- API handles high-quality audio effectively
- Integration produces reliable transcription results

### Scenario: Transcription Error Handling
**Test Method:** `test_assemblyai_error_handling`
**Preconditions:**
- Valid AssemblyAI API key available
- Invalid or corrupted audio file
- Transcription service properly configured

**Integration Flow:**
1. Attempt transcription of invalid audio file
2. Verify graceful error handling
3. Check error messages and status codes
4. Test system stability after transcription errors

**Expected Assertions:**
- Invalid audio handled gracefully without crashes
- Appropriate error messages returned
- Error status codes match AssemblyAI documentation
- System remains stable after transcription failures
- Integration provides meaningful error feedback

## 4. Cross-API Integration Scenarios

### Scenario: Multi-API Workflow Integration
**Test Method:** `test_multi_api_workflow_integration`
**Preconditions:**
- All external API keys available
- Test audio file and reference text
- All services properly configured

**Integration Flow:**
1. Use AssemblyAI for transcription
2. Use OpenAI for grammar and lexical analysis of transcript
3. Use Azure Speech for pronunciation analysis of audio
4. Verify all APIs work together in complete workflow

**Expected Assertions:**
- All APIs integrate successfully in sequence
- Data flows correctly between different services
- No conflicts or interference between API calls
- Complete workflow produces comprehensive results
- Integration maintains data consistency across APIs

### Scenario: API Failure Resilience
**Test Method:** `test_api_failure_resilience`
**Preconditions:**
- Some API keys available, others missing or invalid
- Test data for all services
- Error handling configuration

**Integration Flow:**
1. Attempt workflow with some APIs unavailable
2. Verify graceful degradation of functionality
3. Check that available APIs continue working
4. Test error reporting and logging

**Expected Assertions:**
- Available APIs continue functioning normally
- Unavailable APIs fail gracefully without affecting others
- Appropriate error messages for failed API calls
- System maintains stability with partial API availability
- Error logging provides useful debugging information

### Scenario: API Rate Limiting Handling
**Test Method:** `test_api_rate_limiting_handling`
**Preconditions:**
- Valid API keys with rate limits
- Multiple rapid API calls
- Rate limiting configuration

**Integration Flow:**
1. Make rapid successive calls to external APIs
2. Verify rate limiting detection and handling
3. Test retry mechanisms and backoff strategies
4. Check system behavior under rate limit constraints

**Expected Assertions:**
- Rate limits detected and handled appropriately
- Retry mechanisms work with proper backoff
- System doesn't overwhelm APIs with requests
- Rate limiting doesn't cause system failures
- Integration respects API usage guidelines

## 5. API Configuration and Authentication

### Scenario: API Key Validation
**Test Method:** `test_api_key_validation`
**Preconditions:**
- Various API key configurations (valid, invalid, missing)
- All external services configured

**Integration Flow:**
1. Test with valid API keys
2. Test with invalid API keys
3. Test with missing API keys
4. Verify authentication error handling

**Expected Assertions:**
- Valid keys allow successful API access
- Invalid keys produce appropriate authentication errors
- Missing keys handled gracefully with clear error messages
- Authentication failures don't crash the system
- Error messages help identify configuration issues

### Scenario: API Endpoint Configuration
**Test Method:** `test_api_endpoint_configuration`
**Preconditions:**
- Configurable API endpoints
- Valid and invalid endpoint URLs
- Service configuration options

**Integration Flow:**
1. Test with correct API endpoints
2. Test with incorrect or unreachable endpoints
3. Verify endpoint validation and error handling
4. Check fallback mechanisms if available

**Expected Assertions:**
- Correct endpoints allow successful API communication
- Incorrect endpoints produce appropriate network errors
- Endpoint validation catches configuration issues
- Error messages help identify connectivity problems
- System handles endpoint failures gracefully

## Integration Points Verified

1. **API Communication**
   - HTTP request/response handling with external services
   - Authentication and authorization mechanisms
   - Error handling for network and API failures

2. **Data Format Integration**
   - Request payload formatting for each API
   - Response parsing and validation
   - Data type conversion and schema compliance

3. **Service Coordination**
   - Multi-API workflow orchestration
   - Data flow between different external services
   - Error propagation and recovery mechanisms

4. **Configuration Management**
   - API key and endpoint configuration
   - Service-specific parameter handling
   - Environment-based configuration switching

## Test Coverage Summary

The external API testing covers:
- ✅ OpenAI integration for grammar and lexical analysis
- ✅ Azure Speech integration for pronunciation analysis
- ✅ AssemblyAI integration for transcription services
- ✅ Multi-API workflow coordination
- ✅ API authentication and configuration validation
- ✅ Error handling and resilience testing
- ✅ Rate limiting and usage management
- ✅ Cross-service data flow verification
- ❌ Performance benchmarking across APIs (not implemented)
- ❌ Cost optimization testing (not implemented)
- ❌ API version compatibility testing (not implemented) 