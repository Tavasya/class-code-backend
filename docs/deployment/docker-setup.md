# Docker Setup and Deployment

## 🐳 Docker Configuration

The Audio Analysis API is containerized using Docker for consistent deployment across environments.

## 📋 Dockerfile Analysis

**File**: `Dockerfile` (28 lines)

### Base Image
```dockerfile
FROM python:3.11-slim
```
- Uses Python 3.11 slim image for optimal size and security
- Provides stable Python runtime environment
- Includes essential system libraries

### Working Directory
```dockerfile
WORKDIR /app
```
- Sets `/app` as the container working directory
- All subsequent commands execute in this context

### Dependency Installation
```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
- Copies requirements first for optimal Docker layer caching
- Uses `--no-cache-dir` to reduce image size
- Installs all Python dependencies

### spaCy Model Download
```dockerfile
RUN python -m spacy download en_core_web_sm
```
- Downloads English language model for NLP processing
- Required for vocabulary and linguistic analysis
- Installed at build time for faster container startup

### System Dependencies
```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*
```
- Installs FFmpeg for audio processing
- Uses `--no-install-recommends` to minimize image size
- Cleans up package lists to reduce image size

### Application Code
```dockerfile
COPY . .
```
- Copies all application code into container
- Includes source code, configuration, and assets

### File Permissions
```dockerfile
RUN mkdir -p /app/assets && \
    chmod -R 755 /app/assets
```
- Ensures assets directory exists
- Sets proper permissions for file access
- Handles vocabulary data files

### Port Exposure
```dockerfile
EXPOSE 8080
```
- Exposes port 8080 for HTTP traffic
- Matches the uvicorn server configuration

### Container Command
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```
- Starts the FastAPI application using uvicorn
- Binds to all interfaces (0.0.0.0)
- Uses port 8080 for HTTP traffic

## 🏗️ Build Process

### Local Build
```bash
# Build the Docker image
docker build -t audio-analysis-api .

# Run the container
docker run -p 8080:8080 \
  -e SUPABASE_URL="your_supabase_url" \
  -e SUPABASE_KEY="your_supabase_key" \
  -e OPENAI_API_KEY="your_openai_key" \
  -e AZURE_SPEECH_KEY="your_azure_key" \
  audio-analysis-api
```

### Production Build
```bash
# Build with specific tag
docker build -t gcr.io/your-project/audio-analysis-api:latest .

# Push to registry
docker push gcr.io/your-project/audio-analysis-api:latest
```

## 🔧 Environment Variables

### Required Variables
```bash
# Database Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# OpenAI Configuration
OPENAI_API_KEY=sk-your_openai_api_key

# Azure Speech Services
AZURE_SPEECH_KEY=your_azure_speech_key
AZURE_SPEECH_REGION=eastus

# Optional: AssemblyAI
ASSEMBLYAI_API_KEY=your_assemblyai_key

# Google Cloud (for Pub/Sub)
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

### Development Variables
```bash
# Development settings
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## 📊 Container Resources

### Resource Requirements
```yaml
# Minimum requirements
resources:
  requests:
    memory: "512Mi"
    cpu: "250m"
  limits:
    memory: "2Gi"
    cpu: "1000m"
```

### Optimal Configuration
```yaml
# Recommended for production
resources:
  requests:
    memory: "1Gi"
    cpu: "500m"
  limits:
    memory: "4Gi"
    cpu: "2000m"
```

## 🗂️ Volume Mounts

### Temporary Storage
```bash
# For audio file processing
-v /tmp/audio-processing:/tmp
```
- Persistent storage for temporary audio files
- Improves performance for large files
- Enables cleanup strategies

### Credentials
```bash
# Google Cloud credentials
-v /path/to/gcp-credentials.json:/app/credentials.json
-e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
```

### Assets
```bash
# Vocabulary data files
-v /path/to/assets:/app/assets
```
- External vocabulary databases
- Custom language models
- Configuration files

## 🚀 Deployment Strategies

### Single Container Deployment
```yaml
version: '3.8'
services:
  audio-analysis-api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - AZURE_SPEECH_KEY=${AZURE_SPEECH_KEY}
    volumes:
      - ./assets:/app/assets
      - /tmp:/tmp
    restart: unless-stopped
```

### Multi-Stage Build (Optimized)
```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
RUN python -m spacy download en_core_web_sm
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## 🔍 Health Checks

### Docker Health Check
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/api/v1/health/health || exit 1
```

### Kubernetes Health Check
```yaml
livenessProbe:
  httpGet:
    path: /api/v1/health/health
    port: 8080
  initialDelaySeconds: 60
  periodSeconds: 30
  timeoutSeconds: 10
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/v1/health/health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 5
  failureThreshold: 3
```

## 📈 Performance Optimization

### Image Size Optimization
- Use `.dockerignore` to exclude unnecessary files
- Multi-stage builds to reduce final image size
- Minimize layers by combining RUN commands
- Use slim base images

### Build Cache Optimization
```dockerfile
# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code last
COPY . .
```

### Runtime Performance
```dockerfile
# Use non-root user for security
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Optimize Python performance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
```

## 🔒 Security Considerations

### Base Image Security
- Regularly update base image versions
- Scan images for vulnerabilities
- Use official Python images only

### Secrets Management
```bash
# Use Docker secrets instead of environment variables
docker secret create supabase_key supabase_key.txt
```

### Network Security
```yaml
# Limit container capabilities
security_opt:
  - no-new-privileges:true
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE
```

## 📝 Docker Compose Example

### Development Setup
```yaml
version: '3.8'
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG
    volumes:
      - .:/app
      - /tmp:/tmp
    command: uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

  # Optional: Local Pub/Sub emulator
  pubsub-emulator:
    image: google/cloud-sdk:latest
    ports:
      - "8085:8085"
    command: gcloud beta emulators pubsub start --host-port=0.0.0.0:8085
```

### Production Setup
```yaml
version: '3.8'
services:
  api:
    image: gcr.io/your-project/audio-analysis-api:latest
    ports:
      - "8080:8080"
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    secrets:
      - supabase_key
      - openai_key
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

secrets:
  supabase_key:
    external: true
  openai_key:
    external: true
```

## 🛠️ Troubleshooting

### Common Issues
1. **spaCy model download fails**: Ensure internet connectivity during build
2. **FFmpeg not found**: Verify system dependencies installation
3. **Permission errors**: Check file permissions and user context
4. **Port conflicts**: Ensure port 8080 is available

### Debugging Commands
```bash
# Check container logs
docker logs <container_id>

# Execute commands in running container
docker exec -it <container_id> /bin/bash

# Inspect container configuration
docker inspect <container_id>

# Monitor resource usage
docker stats <container_id>
``` 