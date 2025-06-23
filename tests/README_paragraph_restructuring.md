# Paragraph Restructuring Service Tests

This document describes the comprehensive test suite for the paragraph restructuring service implementation.

## 📁 Test Organization

### 1. **Standalone Service Tests**
**File**: `tests/standalone/test_paragraph_restructuring.py`
**Purpose**: Unit tests for the core service functionality

**Test Categories**:
- ✅ **Band Level Detection**: Tests CEFR level detection from analysis scores
- ✅ **Band Progression Mapping**: Verifies A1→A2, A2→B1, etc. progressions  
- ✅ **OpenAI API Integration**: Mocked API calls and error handling
- ✅ **Service Logic**: Complete restructuring workflow
- ✅ **Error Handling**: Graceful failure scenarios

### 2. **API Endpoint Tests**
**File**: `tests/api/test_paragraph_restructuring_endpoint.py`
**Purpose**: Tests for the FastAPI endpoint functionality

**Test Categories**:
- ✅ **Valid Requests**: Successful paragraph restructuring requests
- ✅ **Auto Band Detection**: Requests without specified band levels
- ✅ **Input Validation**: Empty transcripts, invalid JSON, missing fields
- ✅ **Error Responses**: Service exceptions and API error handling
- ✅ **CEFR Level Variations**: Testing all A1→C2 progressions
- ✅ **Response Schema**: Verifying correct API response structure

### 3. **Integration Tests**
**File**: `tests/integration/test_paragraph_restructuring_integration.py`
**Purpose**: End-to-end workflow testing

**Test Categories**:
- ✅ **Full Workflow**: Complete analysis → band detection → restructuring
- ✅ **Database Integration**: Verify database transformation includes new field
- ✅ **Webhook Simulation**: Simulate submission analysis complete webhook
- ✅ **Error Handling**: Integration-level error scenarios
- ✅ **CEFR Progressions**: Various level transitions in real workflow

## 🚀 Running the Tests

### Run All Paragraph Restructuring Tests
```bash
# All service tests
python -m pytest tests/standalone/test_paragraph_restructuring.py -v

# All API tests  
python -m pytest tests/api/test_paragraph_restructuring_endpoint.py -v

# All integration tests
python -m pytest tests/integration/test_paragraph_restructuring_integration.py -v

# Everything together
python -m pytest tests/ -k "paragraph_restructuring" -v
```

### Run Specific Test Categories
```bash
# Band level detection only
python -m pytest tests/standalone/test_paragraph_restructuring.py -k "band_level" -v

# API endpoint validation only
python -m pytest tests/api/test_paragraph_restructuring_endpoint.py -k "endpoint" -v

# Integration workflow only
python -m pytest tests/integration/test_paragraph_restructuring_integration.py -k "workflow" -v
```

### Run with Verbose Output
```bash
# See detailed test output
python -m pytest tests/standalone/test_paragraph_restructuring.py -v -s
```

## 🎯 Test Coverage

### **Service Functions Tested**
- ✅ `determine_band_level_from_scores()` - CEFR level detection
- ✅ `call_openai_for_restructuring()` - AI API integration  
- ✅ `restructure_paragraph()` - Main service function
- ✅ `analyze_paragraph_restructuring()` - Request handler
- ✅ `get_improvement_instructions()` - CEFR-specific prompts

### **API Endpoint Coverage**
- ✅ `/api/v1/paragraph-restructuring/analysis` - POST endpoint
- ✅ Request validation and error handling
- ✅ Response schema compliance
- ✅ Service integration

### **Integration Points Tested**
- ✅ Webhook processing logic
- ✅ Database transformation with new field
- ✅ Error propagation and handling
- ✅ End-to-end data flow

## 🔍 Key Test Scenarios

### **CEFR Band Detection Test Cases**
```python
# Low scores → A1 
{"pronunciation": 25, "fluency": 20, "grammar": 30} → "A1"

# Medium scores → B1
{"pronunciation": 65, "fluency": 60, "grammar": 70} → "B1"  

# High scores → C1
{"pronunciation": 90, "fluency": 88, "grammar": 92} → "C1"
```

### **Error Handling Scenarios**
- ✅ Empty/invalid analysis results
- ✅ OpenAI API failures (500 errors)
- ✅ Network timeouts and exceptions
- ✅ Invalid transcript inputs
- ✅ Missing required fields

### **Real-World Simulation**
- ✅ Complete submission workflow from webhook
- ✅ Database storage with correct field positioning
- ✅ Multiple question processing
- ✅ Mixed success/failure scenarios

## 📊 Expected Test Results

### **Successful Run Output**
```
tests/standalone/test_paragraph_restructuring.py
✅ 11 tests passed

tests/api/test_paragraph_restructuring_endpoint.py  
✅ 10 tests passed

tests/integration/test_paragraph_restructuring_integration.py
✅ 5 tests passed

Total: 26 tests passed
```

### **Sample Test Output**
```
🎯 Testing Band Level Detection
--------------------------------------------------
Test: Low scores should detect A1
Average Score: 24.0
Expected Band: A1, Detected: A1
Confidence: 1.00
✅ Passed

🤖 Testing Mocked OpenAI Restructuring
--------------------------------------------------
Original: I like to eat food. Food is good.
Improved: I have a strong appreciation for culinary experiences...
✅ API call successful

💾 Testing Database Transform with Paragraph Restructuring
------------------------------------------------------------
Section feedback fields: ['fluency', 'grammar', 'lexical', 'pronunciation', 'paragraph_restructuring', 'vocabulary']
✅ Field positioned correctly after pronunciation
```

## 🧪 Test Data Examples

### **Mock Analysis Results**
```python
analysis_results = {
    "pronunciation": {"grade": 65},
    "fluency": {"grade": 60}, 
    "grammar": {"grade": 70},
    "lexical": {"grade": 62},
    "vocabulary": {"grade": 58}
}
# Expected: B1 → B2 progression
```

### **Mock API Responses**
```python
openai_response = {
    "choices": [{
        "message": {
            "content": "Enhanced paragraph with B2-level vocabulary and structure..."
        }
    }]
}
```

### **Expected Database Structure**
```json
{
  "section_feedback": {
    "fluency": {...},
    "grammar": {...},
    "lexical": {...}, 
    "pronunciation": {...},
    "paragraph_restructuring": {
      "original_band": "B1",
      "target_band": "B2",
      "improved_transcript": "Enhanced version..."
    },
    "vocabulary": {...}
  }
}
```

## 🔧 Test Configuration

### **Mocking Strategy**
- ✅ OpenAI API calls are mocked to avoid real API costs
- ✅ Database operations use test data, not real database
- ✅ Async operations properly tested with pytest-asyncio
- ✅ Error scenarios simulated with controlled exceptions

### **Test Isolation**
- ✅ Each test is independent and can run in any order
- ✅ No shared state between tests
- ✅ Proper setup/teardown for test fixtures
- ✅ Mock cleanup after each test

This comprehensive test suite ensures the paragraph restructuring service is reliable, handles edge cases gracefully, and integrates properly with the existing analysis pipeline. 