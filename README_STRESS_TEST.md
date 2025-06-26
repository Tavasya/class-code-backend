# Audio Analysis System Stress Test

This stress testing suite is designed to identify scaling bottlenecks and performance issues in the audio analysis system under concurrent load.

## Quick Start

### 1. Install Dependencies
```bash
pip install aiohttp psutil
```

### 2. Basic Test (5 concurrent users)
```bash
python stress_test.py
```

### 3. Custom Configuration
```bash
python stress_test.py --concurrent-users 10 --test-duration 600
```

## Configuration Options

### Command Line Arguments
- `--concurrent-users` - Number of concurrent users (default: 5)
- `--requests-per-user` - Requests per user (default: 10)  
- `--test-duration` - Max test duration in seconds (default: 300)
- `--base-url` - API base URL (default: http://localhost:8080)
- `--config` - JSON configuration file
- `--test-data` - JSON file with real test data
- `--report-file` - Output file for detailed report

### Configuration File
Use `stress_test_config.json` for detailed configuration:

```json
{
  "base_url": "http://localhost:8080",
  "concurrent_users": 5,
  "requests_per_user": 10,
  "test_duration": 300,
  "request_timeout": 60,
  "ramp_up_time": 30,
  "think_time_min": 1,
  "think_time_max": 5
}
```

## Test Data Setup

### 1. Replace Template Data
Edit `test_data_template.json` with your actual submission data:

```json
[
  {
    "submission_id": "your_actual_submission_id_1",
    "audio_url": "https://your-storage.com/audio1.wav",
    "expected_duration": 45,
    "metadata": {
      "test_case": "real_case_1",
      "complexity": "medium",
      "language": "en",
      "speaker_level": "intermediate"
    }
  }
]
```

### 2. Run with Real Data
```bash
python stress_test.py --test-data test_data_template.json
```

## Test Scenarios

### Scenario 1: Current System Limits
Test the documented limits of 5-10 concurrent requests:
```bash
python stress_test.py --concurrent-users 5 --requests-per-user 5
python stress_test.py --concurrent-users 10 --requests-per-user 5
```

### Scenario 2: Breaking Point Analysis
Find where the system fails:
```bash
python stress_test.py --concurrent-users 15 --requests-per-user 3
python stress_test.py --concurrent-users 20 --requests-per-user 3
```

### Scenario 3: Sustained Load
Test sustained performance:
```bash
python stress_test.py --concurrent-users 5 --test-duration 900 --requests-per-user 20
```

### Scenario 4: Memory Leak Detection
Long-running test for memory issues:
```bash
python stress_test.py --concurrent-users 3 --test-duration 1800 --requests-per-user 50
```

## Understanding Results

### Success Metrics
- **Success Rate**: Should be >95% for production readiness
- **Response Time**: Should be <30s average for good UX
- **Throughput**: Requests processed per second
- **Resource Usage**: CPU, Memory, Disk utilization

### Warning Signs
- **Success Rate <90%**: System instability under load
- **Response Time >60s**: Performance bottlenecks present
- **Memory Growth**: Potential memory leaks
- **High Error Rate**: Scaling issues

### Report Interpretation

The stress test generates detailed reports in JSON format:

```json
{
  "test_summary": {
    "success_rate_percent": 85.5,
    "requests_per_second": 2.3,
    "total_requests": 50,
    "failed_requests": 7
  },
  "response_time_stats": {
    "average_seconds": 45.2,
    "p95_seconds": 78.1
  },
  "system_resources": {
    "memory": {"max": 89.2, "avg": 67.1},
    "cpu": {"max": 95.6, "avg": 73.4}
  },
  "recommendations": [
    "High memory usage detected - potential memory leaks",
    "Consider implementing connection pooling and rate limiting"
  ]
}
```

## Expected Results (Current System)

Based on the architectural analysis, expect these results:

### 5 Concurrent Users
- **Success Rate**: 60-80%
- **Average Response Time**: 45-90 seconds
- **Memory Usage**: Steadily increasing
- **Common Errors**: Timeouts, memory errors

### 10+ Concurrent Users  
- **Success Rate**: <50%
- **System**: Likely crashes or becomes unresponsive
- **Memory**: Rapid growth leading to OOM
- **Errors**: Connection failures, service unavailable

## Monitoring During Tests

The stress test automatically monitors:
- **CPU Usage**: Process and system level
- **Memory Usage**: RAM consumption and deltas
- **Disk Usage**: Storage utilization
- **Network I/O**: Bytes sent/received
- **Response Times**: Per-request timing
- **Error Rates**: Success/failure tracking

## Troubleshooting

### Test Fails to Start
```bash
# Check if server is running
curl http://localhost:8080/health

# Check dependencies
pip install aiohttp psutil
```

### High Error Rates
1. Reduce concurrent users
2. Increase timeouts
3. Check server logs
4. Monitor system resources

### Memory Issues
1. Monitor system memory during test
2. Check for proper cleanup in server code
3. Review file handling and caching

### Connection Errors
1. Check connection limits
2. Verify server capacity
3. Review network configuration

## Next Steps

After running stress tests:

1. **Document Current Limits**: Record max concurrent users
2. **Identify Bottlenecks**: CPU, Memory, Database, API limits
3. **Plan Optimizations**: Use results to prioritize improvements
4. **Re-test After Changes**: Validate improvements

## Integration with Analysis Document

These stress test results directly validate the scaling issues identified in `PROMPT_OPTIMIZATION_ANALYSIS.md`. Use the test data to:

1. Confirm current system limits (5-10 concurrent requests)
2. Validate memory leak issues
3. Document state management problems
4. Measure improvement after Redis implementation

The stress test serves as both a diagnostic tool and a validation mechanism for the proposed Redis-based scaling solutions.