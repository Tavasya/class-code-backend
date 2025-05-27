# Health Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/health.py` - Health endpoint implementation
- `app/core/config.py` - Configuration and Supabase connection
- `app/models/schemas.py` - HealthResponse model
- `app/core/config.py` - Environment configuration

## 1. Basic Health Check

### Scenario: Successful Health Check
**Preconditions:**
- Mock Supabase client connected
- Environment variables set
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- HTTP status code 200
- Response matches `HealthResponse` schema
- Response contains required fields:
  - `status`: "STAGE BRANCH ISS HEALTHYY"
  - `timestamp`: Valid ISO format datetime
  - `environment`: Current environment value
  - `supabase`: "connected"

### Scenario: Missing Environment Variable
**Preconditions:**
- Mock Supabase client connected
- `ENVIRONMENT` environment variable not set
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- HTTP status code 200
- Response contains:
  - `environment`: "development" (default value)
  - Other fields present and valid

## 2. Supabase Connection Status

### Scenario: Supabase Connected
**Preconditions:**
- Mock Supabase client successfully initialized
- Valid Supabase configuration
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- HTTP status code 200
- Response contains:
  - `supabase`: "connected"
- Supabase client properly initialized

### Scenario: Supabase Not Connected
**Preconditions:**
- Mock Supabase client as None
- Missing or invalid Supabase configuration
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- HTTP status code 200
- Response contains:
  - `supabase`: "not connected"
- Health check still succeeds despite Supabase issue

## 3. Response Format Validation

### Scenario: Response Schema Compliance
**Preconditions:**
- Mock all dependencies
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- Response follows `HealthResponse` model exactly
- All required fields present
- Field types match model definition
- No extra fields in response

### Scenario: Timestamp Format Validation
**Preconditions:**
- Mock datetime.now()
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- `timestamp` field is valid ISO 8601 format
- Timestamp represents current time
- Timezone information included

## 4. Environment Configuration

### Scenario: Development Environment
**Preconditions:**
- Set `ENVIRONMENT=development`
- Mock dependencies
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- Response contains:
  - `environment`: "development"

### Scenario: Production Environment
**Preconditions:**
- Set `ENVIRONMENT=production`
- Mock dependencies
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- Response contains:
  - `environment`: "production"

### Scenario: Staging Environment
**Preconditions:**
- Set `ENVIRONMENT=staging`
- Mock dependencies
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- Response contains:
  - `environment`: "staging"

## 5. Error Handling

### Scenario: Internal Server Error
**Preconditions:**
- Mock datetime.now() to raise exception
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- HTTP status code 500
- Error response returned
- Exception handled gracefully

## 6. Performance and Reliability

### Scenario: Response Time Validation
**Preconditions:**
- Mock all dependencies
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`
2. Measure response time

**Expected Assertions:**
- Response time under 100ms
- Consistent response times across multiple calls

### Scenario: Concurrent Health Checks
**Preconditions:**
- Mock all dependencies
- Clean application state

**User Actions:**
1. Send multiple concurrent GET requests to `/api/v1/health/`

**Expected Assertions:**
- All requests return HTTP 200
- No race conditions or errors
- Consistent responses across all calls

## Integration Points to Verify

1. **Configuration Integration**
   - Environment variable reading
   - Default value handling
   - Supabase client status detection

2. **Response Model Integration**
   - Pydantic model validation
   - Proper serialization
   - Schema compliance

3. **Dependency Status**
   - Supabase connection verification
   - External service health indicators
   - Graceful handling of dependency failures 