# FlowTracer 

AI-powered Python SDK that traces data flow through your applications with human-readable insights.

## Quick Start

1. **Install dependencies:**
```bash
pip install supabase openai
```

2. **Setup database:**
```bash
export SUPABASE_URL="your-supabase-url"
export SUPABASE_SERVICE_KEY="your-service-key"
python supabase/setup.py
```

3. **Use in your code:**
```python
from flowtracer import init_tracer, trace_flow, start_flow

# Initialize once
init_tracer(
    supabase_url="your-supabase-url",
    supabase_key="your-supabase-key",
    openai_api_key="your-openai-key"
)

# Trace your functions
@trace_flow()
def process_payment(data):
    return validate_payment(data)

@trace_flow()
def validate_payment(data):
    # Your logic here
    return data

# Track API requests
def handle_request(request_id, endpoint, data):
    with start_flow(request_id, endpoint):
        return process_payment(data)
```

## What You Get

- **Human-readable flow names**: AI converts `validate_user_input()` → "Validate Input"
- **Tree structure**: See parent-child relationships between function calls
- **Concurrency tracking**: Understand sequential vs parallel execution
- **Performance insights**: Find your slowest functions
- **Real-time updates**: Watch flows as they happen (via WebSocket)

## Example Output

Instead of seeing cryptic function names, you get readable flows:
```
API Request: /api/register
├── Validate Input (12ms)
├── Create Account (45ms)
│   ├── Check Duplicates (8ms)
│   └── Save User (23ms)
└── Send Email (15ms, async)
```

## Database Queries

Check `supabase/queries.sql` for useful analysis queries:
- Find slowest functions
- Identify error patterns  
- Analyze concurrency
- Track performance over time

## Cost Optimization

- **Fixed AI cost**: Batches 10 function names per OpenAI call
- **Smart caching**: Reuses AI-generated names
- **Minimal overhead**: Only active during traced flows