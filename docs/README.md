# Audio Analysis API Documentation

This directory contains comprehensive documentation for the Audio Analysis API codebase, which is a FastAPI-based backend system for analyzing audio submissions, particularly for language learning applications.

## 📋 Documentation Overview

This documentation is organized into several sections to help you understand different aspects of the codebase:

### 🏗️ Architecture
- [`architecture/system-overview.md`](architecture/system-overview.md) - High-level system architecture and components
- [`architecture/data-flow.md`](architecture/data-flow.md) - How data flows through the system
- [`architecture/pubsub-messaging.md`](architecture/pubsub-messaging.md) - Pub/Sub messaging architecture

### 🔌 API Documentation
- [`api/endpoints-overview.md`](api/endpoints-overview.md) - Complete list of API endpoints
- [`api/submission-flow.md`](api/submission-flow.md) - How audio submissions are processed
- [`api/webhook-integration.md`](api/webhook-integration.md) - Webhook endpoints and integration

### ⚙️ Services
- [`services/analysis-services.md`](services/analysis-services.md) - Core analysis services (pronunciation, fluency, etc.)
- [`services/audio-processing.md`](services/audio-processing.md) - Audio conversion and processing
- [`services/database-service.md`](services/database-service.md) - Database operations with Supabase

### 📊 Data Models
- [`models/data-structures.md`](models/data-structures.md) - Pydantic models and data structures
- [`models/api-schemas.md`](models/api-schemas.md) - Request/response schemas

### 🚀 Deployment
- [`deployment/docker-setup.md`](deployment/docker-setup.md) - Docker configuration and deployment
- [`deployment/environment-variables.md`](deployment/environment-variables.md) - Environment configuration
- [`deployment/cloud-deployment.md`](deployment/cloud-deployment.md) - Google Cloud Run deployment

### 🧪 Testing
- [`testing/test-structure.md`](testing/test-structure.md) - Testing organization and strategies
- [`testing/integration-testing.md`](testing/integration-testing.md) - Integration test documentation

## 🎯 Quick Start

If you're new to this codebase, start with:
1. [`architecture/system-overview.md`](architecture/system-overview.md) - Understand what this system does
2. [`api/submission-flow.md`](api/submission-flow.md) - Learn how audio submissions work
3. [`services/analysis-services.md`](services/analysis-services.md) - Understand the core analysis capabilities

## 🔧 Technology Stack

- **Framework**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **Messaging**: Google Cloud Pub/Sub
- **Audio Processing**: FFmpeg, Azure Speech Services
- **AI/ML**: OpenAI API, spaCy NLP
- **Deployment**: Docker, Google Cloud Run

## 📝 Contributing

When adding new features or making changes:
1. Update relevant documentation files
2. Follow the existing documentation structure
3. Include code examples where helpful
4. Update this main README if adding new documentation sections 