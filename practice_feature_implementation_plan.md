# Practice Feature Implementation Plan

## Executive Summary

The practice feature will provide real-time transcript analysis and pronunciation feedback to users, operating independently from the existing pub/sub submission pipeline. This feature will reuse existing AI services while maintaining architectural separation for optimal performance.

## Current System Analysis

### Existing Architecture Components to Leverage
- **Transcription Services**: AssemblyAI and Azure Speech Services (app/services/transcription_service.py)
- **Pronunciation Analysis**: CMU Dictionary-based phoneme analysis (app/services/pronunciation_service.py)
- **Improvement Engine**: OpenAI GPT-4 powered paragraph restructuring (app/services/paragraph_restructuring_service.py)
- **Webhook Infrastructure**: 11 existing webhook handlers with retry logic (app/pubsub/webhooks/)
- **Database Layer**: Supabase integration with real-time capabilities (app/services/database_service.py)
- **Real-time Features**: Supabase Realtime and status tracking systems

### Current Limitations for Practice Use Case
- **Heavy Processing Pipeline**: 11-stage pub/sub flow optimized for comprehensive analysis, not speed
- **Assignment Dependency**: Current flow tied to assignment/submission structure
- **Complex Orchestration**: Analysis coordinator waits for multiple services before proceeding
- **Comprehensive Analysis**: All 5 analysis types run regardless of user needs

## Practice Feature Requirements

### Core Functionality
1. **Transcript Analysis**: Take user audio/text and provide immediate improvement suggestions
2. **Pronunciation Analysis**: Real-time phoneme-level pronunciation feedback
3. **Real-time Delivery**: Webhook-based immediate feedback system
4. **Independent Operation**: Completely separate from existing pub/sub assignment flow
5. **Session Management**: Track practice sessions independently from formal submissions

### Performance Requirements
- **Response Time**: < 5 seconds for transcript analysis
- **Real-time Feedback**: Webhook delivery within 2 seconds of completion
- **Concurrent Sessions**: Support 100+ simultaneous practice sessions
- **Scalability**: Independent scaling from main grading pipeline

## Technical Implementation Plan

### Phase 1: Core Infrastructure

#### 1.1 Database Schema Extensions
**New Tables in Supabase:**
```sql
-- Practice Sessions
practice_sessions (
    id UUID PRIMARY KEY,
    user_id TEXT,
    created_at TIMESTAMP,
    status TEXT, -- 'active', 'completed', 'abandoned'
    session_type TEXT, -- 'transcript_practice', 'pronunciation_practice'
    metadata JSONB
)

-- Practice Requests
practice_requests (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES practice_sessions(id),
    request_type TEXT, -- 'audio', 'transcript'
    input_data JSONB, -- audio_url or transcript_text
    created_at TIMESTAMP,
    status TEXT -- 'pending', 'processing', 'completed', 'failed'
)

-- Practice Results
practice_results (
    id UUID PRIMARY KEY,
    request_id UUID REFERENCES practice_requests(id),
    result_type TEXT, -- 'improvements', 'pronunciation', 'combined'
    feedback_data JSONB,
    processing_time_ms INTEGER,
    created_at TIMESTAMP
)
```

#### 1.2 Practice Models (app/models/practice_models.py)
```python
class PracticeSession(BaseModel):
    id: str
    user_id: str
    session_type: str  # 'transcript_practice' | 'pronunciation_practice'
    status: str  # 'active' | 'completed' | 'abandoned'
    created_at: datetime
    metadata: Dict[str, Any]

class PracticeRequest(BaseModel):
    id: str
    session_id: str
    request_type: str  # 'audio' | 'transcript'
    input_data: Dict[str, Any]  # {audio_url: str} or {transcript_text: str}
    status: str  # 'pending' | 'processing' | 'completed' | 'failed'

class PracticeImprovement(BaseModel):
    original_text: str
    improved_text: str
    improvements: List[ImprovementSuggestion]
    cefr_level: str
    overall_score: float

class PronunciationFeedback(BaseModel):
    word_scores: List[WordPronunciationScore]
    overall_accuracy: float
    critical_errors: List[PronunciationError]
    practice_suggestions: List[str]
```

#### 1.3 Practice Service Layer (app/services/practice_service.py)
```python
class PracticeService:
    def create_session(user_id: str, session_type: str) -> PracticeSession
    def submit_for_analysis(session_id: str, input_data: Dict) -> PracticeRequest
    def get_session_results(session_id: str) -> List[PracticeResult]
    def complete_session(session_id: str) -> PracticeSession
    
    # Direct service integrations (bypassing pub/sub)
    def analyze_transcript_direct(transcript: str) -> PracticeImprovement
    def analyze_pronunciation_direct(audio_url: str, transcript: str) -> PronunciationFeedback
```

### Phase 2: API Endpoints

#### 2.1 Practice API Router (app/api/v1/endpoints/practice_endpoint.py)
```python
# Session Management
POST /api/v1/practice/sessions
GET /api/v1/practice/sessions/{session_id}
PUT /api/v1/practice/sessions/{session_id}/complete

# Practice Analysis
POST /api/v1/practice/analyze/transcript
POST /api/v1/practice/analyze/pronunciation
POST /api/v1/practice/analyze/combined

# Results Retrieval
GET /api/v1/practice/sessions/{session_id}/results
GET /api/v1/practice/requests/{request_id}/result
```

#### 2.2 Webhook Integration (app/pubsub/webhooks/practice_webhooks.py)
```python
# New Pub/Sub Topics
PRACTICE_TRANSCRIPT_ANALYSIS_TOPIC = "practice-transcript-analysis"
PRACTICE_PRONUNCIATION_ANALYSIS_TOPIC = "practice-pronunciation-analysis"
PRACTICE_ANALYSIS_COMPLETE_TOPIC = "practice-analysis-complete"

# Webhook Endpoints
POST /api/v1/webhooks/practice-transcript-complete
POST /api/v1/webhooks/practice-pronunciation-complete
POST /api/v1/webhooks/practice-analysis-complete
```

### Phase 3: Real-time Processing Pipeline

#### 3.1 Practice Analysis Orchestrator (app/services/practice_orchestrator.py)
```python
class PracticeOrchestrator:
    # Simplified pipeline - no complex coordination
    def process_transcript_practice(request: PracticeRequest) -> None:
        # 1. Direct call to paragraph_restructuring_service
        # 2. Immediate webhook notification
        # 3. Store results in practice_results table
        
    def process_pronunciation_practice(request: PracticeRequest) -> None:
        # 1. Direct call to transcription_service (if audio)
        # 2. Direct call to pronunciation_service
        # 3. Immediate webhook notification
        # 4. Store results in practice_results table
```

#### 3.2 Practice-Specific Service Adaptations
```python
# Fast Transcript Analysis (app/services/practice_transcript_service.py)
class PracticeTranscriptService:
    def analyze_for_practice(transcript: str) -> PracticeImprovement:
        # Optimized for speed - single OpenAI call
        # Focus on top 3-5 improvements
        # Simplified CEFR assessment
        
# Fast Pronunciation Analysis (app/services/practice_pronunciation_service.py)
class PracticePronunciationService:
    def analyze_for_practice(audio_url: str, transcript: str) -> PronunciationFeedback:
        # Reuse existing pronunciation_service.analyze_pronunciation()
        # Filter to critical errors only
        # Simplified word-level scoring
```

### Phase 4: Real-time Delivery System

#### 4.1 Practice Webhook Handlers
```python
class PracticeWebhookHandler:
    def handle_transcript_complete(message: PubSubMessage) -> None:
        # Extract practice_request_id from message
        # Retrieve results from database
        # Send webhook to frontend immediately
        
    def handle_pronunciation_complete(message: PubSubMessage) -> None:
        # Extract practice_request_id from message
        # Retrieve results from database
        # Send webhook to frontend immediately
```

#### 4.2 Frontend Integration Points
```python
# Webhook payload to frontend
{
    "practice_request_id": "uuid",
    "session_id": "uuid",
    "result_type": "improvements" | "pronunciation" | "combined",
    "feedback_data": {
        # Structured feedback based on result_type
    },
    "processing_time_ms": 2500,
    "timestamp": "2024-01-01T12:00:00Z"
}
```

## Architecture Differences from Main Pipeline

### Simplified Flow
**Current Main Pipeline:** 11 stages, complex orchestration
**Practice Pipeline:** 3 stages maximum
1. Input validation & session creation
2. Direct service analysis
3. Immediate webhook delivery

### Independent Scaling
- **Separate Database Tables**: No impact on main submission tables
- **Dedicated Pub/Sub Topics**: Practice messages don't interfere with grading
- **Independent Service Instances**: Can scale practice services separately

### Performance Optimizations
- **Direct Service Calls**: Bypass pub/sub coordination for faster response
- **Simplified Analysis**: Focus on immediate actionable feedback
- **Reduced Data Storage**: Store only essential practice results

## Implementation Timeline

### Week 1-2: Infrastructure Setup
- Create practice database tables
- Implement practice models and service layer
- Set up practice-specific pub/sub topics

### Week 3-4: API Development
- Build practice API endpoints
- Implement direct service integrations
- Create practice webhook handlers

### Week 5-6: Real-time Integration
- Implement practice orchestrator
- Set up webhook delivery system
- Add frontend integration points

### Week 7-8: Testing & Optimization
- Performance testing with concurrent sessions
- Optimize response times
- Add monitoring and analytics

## Risk Mitigation

### Technical Risks
- **Service Overload**: Independent scaling prevents impact on main pipeline
- **Database Bottlenecks**: Separate tables with optimized indexes
- **Webhook Failures**: Reuse existing retry logic and error handling

### Operational Risks
- **Cost Management**: Practice sessions tracked separately for billing
- **Resource Allocation**: Independent service instances for practice workload
- **Monitoring**: Dedicated dashboards for practice feature performance

## Success Metrics

### Performance Targets
- **Response Time**: < 5 seconds for transcript analysis
- **Webhook Delivery**: < 2 seconds after processing completion
- **Concurrent Sessions**: Support 100+ simultaneous practice sessions
- **Uptime**: 99.9% availability for practice endpoints

### User Experience Metrics
- **Practice Session Completion Rate**: > 80%
- **User Satisfaction**: Measured through feedback surveys
- **Feature Adoption**: Track weekly active practice users

This implementation plan provides a complete practice feature while maintaining architectural separation and reusing proven system components.