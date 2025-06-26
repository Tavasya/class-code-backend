# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
- **Run all tests**: `python run_tests.py all`
- **Run specific service tests**: `python run_tests.py [service]`
  - Available services: `vocabulary`, `grammar`, `transcription`, `fluency`, `audio`, `pronunciation`
- **Run API tests**: `python run_tests.py api`
- **Run standalone service tests**: `python run_tests.py standalone`
- **Run specific test file**: `python -m pytest tests/path/to/test_file.py -v`

### Running the Application
- **Local development**: `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080`
- **Production mode**: `python app/main.py`
- **Docker build**: `docker build -t audio-analysis-api .`
- **Docker run**: `docker run -p 8080:8080 audio-analysis-api`

### Environment Setup
- **Install dependencies**: `pip install -r requirements.txt`
- **Download spaCy model**: `python -m spacy download en_core_web_sm`
- **Install FFmpeg**: Required for audio processing (system dependency)

## Architecture Overview

This is an **event-driven microservices** audio analysis API built with FastAPI that provides comprehensive spoken language assessment for educational applications.

### Core Components

1. **FastAPI Application** (`app/main.py`): Main server with CORS, Sentry integration, and background cleanup tasks
2. **API Layer** (`app/api/v1/`): REST endpoints for audio submission, analysis retrieval, and health checks
3. **Analysis Services** (`app/services/`): 11 independent services for different analysis types
4. **Pub/Sub System** (`app/pubsub/`): Google Cloud Pub/Sub messaging for asynchronous processing
5. **Data Models** (`app/models/`): Pydantic models for type safety and validation

### Analysis Pipeline

The system processes audio submissions through this flow:
1. **Audio Submission** → Upload audio URL via REST API
2. **Parallel Processing** → Audio conversion (WAV) + Speech transcription
3. **Analysis Coordination** → Waits for prerequisites, then triggers analysis services
4. **Parallel Analysis** → 5 analysis services run simultaneously:
   - **Pronunciation** (`pronunciation_service.py`): Phoneme accuracy, stress patterns
   - **Fluency** (`fluency_service.py`): Speech rate, pause analysis, filler detection
   - **Grammar** (`grammar_service.py`): OpenAI GPT integration for grammar checking
   - **Lexical** (`lexical_service.py`): Vocabulary sophistication, diversity
   - **Vocabulary** (`vocabulary_service.py`): Enhancement suggestions, synonyms
5. **Result Aggregation** → Combined analysis results stored in Supabase
6. **Webhook Notification** → Frontend notified of completion

### Key Services

- **Audio Service** (`audio_service.py`): FFmpeg-based audio conversion and processing
- **Transcription Service** (`transcription_service.py`): Azure Speech Services integration
- **Database Service** (`database_service.py`): Supabase PostgreSQL interface
- **File Manager Service** (`file_manager_service.py`): Temporary file cleanup and management
- **Analysis Coordinator** (`analysis_coordinator_service.py`): Orchestrates the analysis pipeline

### Message Topics & Webhooks

The system uses 11 Pub/Sub topics for service communication:
- `audio-submission`, `audio-conversion`, `transcription-request`
- `analysis-coordination`, `pronunciation-analysis`, `fluency-analysis`
- `grammar-analysis`, `lexical-analysis`, `vocabulary-analysis`
- `analysis-complete`, `submission-complete`

Webhooks notify external systems when processing completes.

### External Dependencies

- **Supabase**: PostgreSQL database for result storage
- **OpenAI API**: Grammar analysis via GPT models
- **Azure Speech Services**: Audio transcription
- **Google Cloud Pub/Sub**: Asynchronous messaging
- **Sentry**: Error monitoring and performance tracking

### File Structure Notes

- Tests are organized into `standalone/` (service unit tests) and `api/` (integration tests)
- Documentation in `docs/` includes architecture diagrams and API specifications
- Model evaluation tools in `model_evaluation/` for analysis quality assessment
- Assets directory contains vocabulary reference files

## Configuration

Required environment variables:
- `SUPABASE_URL`, `SUPABASE_KEY`: Database connection
- `OPENAI_API_KEY`: Grammar analysis
- `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`: Transcription
- `GOOGLE_CLOUD_PROJECT`: Pub/Sub messaging

Optional:
- `ASSEMBLYAI_API_KEY`: Alternative transcription service
- `DEBUG`, `LOG_LEVEL`: Development settings