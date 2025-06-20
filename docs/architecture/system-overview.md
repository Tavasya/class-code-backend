# System Overview

## 🎯 Purpose

The Audio Analysis API is a sophisticated backend system designed to analyze audio submissions for language learning applications. It provides comprehensive analysis of spoken language including pronunciation, fluency, grammar, vocabulary, and lexical complexity assessment.

## 🏗️ High-Level Architecture

```
Frontend Application
       ↓
   FastAPI Server
       ↓
  Pub/Sub Messaging ← → Analysis Services
       ↓                     ↓
   Supabase DB          External APIs
                        (OpenAI, Azure)
```

## 🧩 Core Components

### 1. **FastAPI Application** (`app/main.py`)
- Central web server built with FastAPI framework
- Handles HTTP requests and responses
- Manages CORS for frontend integration
- Includes background tasks for file cleanup
- Initializes vocabulary tools on startup

### 2. **API Layer** (`app/api/`)
- **v1 Router**: Organizes all API endpoints
- **Endpoints**: Individual endpoint handlers for different functionalities
- RESTful API design with proper HTTP status codes
- Request/response validation using Pydantic models

### 3. **Service Layer** (`app/services/`)
The business logic core of the application:

- **Analysis Coordinator**: Orchestrates the entire analysis workflow
- **Audio Service**: Handles audio file conversion and processing
- **Transcription Service**: Manages speech-to-text conversion
- **Analysis Services**: 
  - Pronunciation analysis
  - Fluency assessment
  - Grammar checking
  - Vocabulary analysis
  - Lexical complexity evaluation
- **Database Service**: Handles all database operations
- **File Manager**: Manages temporary file lifecycle

### 4. **Pub/Sub Messaging System** (`app/pubsub/`)
- **Google Cloud Pub/Sub integration**
- **Topic-based messaging** for loose coupling
- **Asynchronous processing** of analysis tasks
- **Message handlers** for different analysis stages
- **Webhooks** for external system integration

### 5. **Data Models** (`app/models/`)
- **Pydantic models** for type safety and validation
- **Request/Response schemas** for API endpoints
- **Message models** for Pub/Sub communication
- **Analysis result models** for structured data

### 6. **Configuration** (`app/core/`)
- **Environment-based configuration**
- **External service credentials** (Supabase, OpenAI, Azure)
- **CORS settings** for frontend integration
- **Pub/Sub topic/subscription definitions**

## 🔄 Processing Workflow

### Audio Submission Flow:
1. **Frontend submits** audio URLs via `/api/v1/submission/submit`
2. **Submission service** validates and queues audio for processing
3. **Audio service** converts audio to WAV format
4. **Transcription service** converts speech to text
5. **Analysis coordinator** waits for both audio and transcript completion
6. **Analysis services** perform parallel analysis:
   - Pronunciation scoring
   - Fluency assessment
   - Grammar evaluation
   - Vocabulary analysis
   - Lexical complexity scoring
7. **Results aggregation** and storage in database
8. **Webhook notification** to frontend with results

## 🛠️ Technology Stack

### Backend Framework
- **FastAPI**: Modern, fast web framework for building APIs
- **Uvicorn**: ASGI server for production deployment
- **Pydantic**: Data validation and settings management

### External Services
- **Supabase**: PostgreSQL database with real-time capabilities
- **Google Cloud Pub/Sub**: Scalable messaging service
- **OpenAI API**: GPT models for advanced language analysis
- **Azure Speech Services**: Speech-to-text transcription
- **AssemblyAI**: Alternative transcription service

### Audio Processing
- **FFmpeg**: Audio format conversion and processing
- **spaCy**: Natural language processing toolkit
- **CMU Dictionary**: Phonetic analysis for pronunciation

### Development Tools
- **Docker**: Containerization for consistent deployment
- **GitHub Actions**: CI/CD pipeline automation
- **Python dotenv**: Environment variable management

## 📊 Data Flow

### Synchronous Operations:
- API request handling
- Input validation
- Basic audio metadata extraction

### Asynchronous Operations:
- Audio format conversion
- Speech transcription
- Complex analysis tasks
- Database operations
- Webhook notifications

## 🔐 Security Features

- **CORS configuration** for frontend security
- **Environment variable protection** for sensitive credentials
- **Request validation** using Pydantic models
- **Error handling** with proper logging
- **File cleanup** to prevent storage bloat

## 📈 Scalability Design

- **Microservice-like architecture** with service separation
- **Pub/Sub messaging** for loose coupling
- **Stateless design** for horizontal scaling
- **External service integration** for specialized tasks
- **Background task management** for long-running operations

## 🔧 Configuration Management

The system uses environment variables for configuration:
- Database credentials
- API keys for external services
- CORS origins for frontend integration
- Pub/Sub project settings
- Azure Speech service configuration

## 🚀 Deployment Ready

- **Docker containerization** with multi-stage builds
- **Google Cloud Run** deployment configuration
- **GitHub Actions** for automated deployment
- **Health check endpoints** for monitoring
- **Proper logging** for debugging and monitoring 