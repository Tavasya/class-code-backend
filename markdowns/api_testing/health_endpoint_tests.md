# Health Endpoint API Test Plan

## Files to Reference
- `app/api/v1/endpoints/health.py` - Health endpoint implementation
- `app/core/config.py` - Configuration and Supabase connection
- `app/main.py` - FastAPI application instance

## Test Setup
- Uses `TestClient` from FastAPI for endpoint testing
- Mocks `supabase` from `app.core.config` module
- All tests use the endpoint `/api/v1/health/`
- Uses `patch.dict` for environment variable testing

## 1. Basic Health Check

### Scenario: Successful Health Check
**Test Method:** `test_health_check_success`
**Preconditions:**
- Mock Supabase client with `MagicMock()`
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- HTTP status code 200
- Response data contains: `"status": "STAGE BRANCH ISS HEALTHYY"`
- Response contains `"timestamp"` field
- Response contains `"environment"` field
- Response data contains: `"supabase": "connected"`

## 2. Supabase Connection Status

### Scenario: Supabase Connected
**Test Method:** `test_supabase_connected`
**Preconditions:**
- Mock Supabase client with `MagicMock()`
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- Response data contains: `"supabase": "connected"`
- Supabase client properly mocked and detected as connected

## 3. Environment Configuration

### Scenario: Default Environment When Not Set
**Test Method:** `test_environment_default`
**Preconditions:**
- Mock Supabase client with `MagicMock()`
- Clear all environment variables using `patch.dict(os.environ, {}, clear=True)`
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- HTTP status code 200
- Response data contains: `"environment": "development"`
- Default environment value used when ENVIRONMENT variable not set

### Scenario: Custom Environment Setting
**Test Method:** `test_environment_custom`
**Preconditions:**
- Mock Supabase client with `MagicMock()`
- Set environment variable using `patch.dict(os.environ, {"ENVIRONMENT": "production"})`
- Clean application state

**User Actions:**
1. Send GET request to `/api/v1/health/`

**Expected Assertions:**
- HTTP status code 200
- Response data contains: `"environment": "production"`
- Custom environment variable value properly read and returned

## Integration Points Verified

1. **Configuration Integration**
   - Environment variable reading with `os.environ.get("ENVIRONMENT", "development")`
   - Default value handling for missing environment variables
   - Supabase client status detection from `app.core.config.supabase`

2. **Response Format**
   - Consistent response structure across all scenarios
   - Required fields: status, timestamp, environment, supabase
   - Proper JSON serialization

3. **Dependency Status**
   - Supabase connection verification through mocking
   - Graceful handling when dependencies are mocked
   - Status reporting for external service connections

## Test Coverage Summary

The health endpoint tests cover:
- ✅ Basic health check functionality
- ✅ Supabase connection status reporting
- ✅ Environment variable handling (default and custom)
- ✅ Response format validation
- ❌ Error handling scenarios (not implemented)
- ❌ Performance testing (not implemented)
- ❌ Concurrent request handling (not implemented) 