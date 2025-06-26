from flowtracer import init_tracer, trace_flow, start_flow
import time
import asyncio

# Initialize the tracer
init_tracer(
    supabase_url="your-supabase-url",
    supabase_key="your-supabase-key", 
    openai_api_key="your-openai-key"
)

# Example API endpoint
@trace_flow("User Registration")
def register_user(user_data):
    validated_data = validate_user_input(user_data)
    user = create_user_account(validated_data)
    send_welcome_email(user)
    return user

@trace_flow()
def validate_user_input(data):
    # Simulate validation
    time.sleep(0.1)
    return {**data, 'validated': True}

@trace_flow()
def create_user_account(data):
    # Simulate database operation
    time.sleep(0.2)
    return {'id': 123, **data}

@trace_flow()
async def send_welcome_email(user):
    # Simulate async email sending
    await asyncio.sleep(0.1)
    print(f"Email sent to user {user['id']}")

# Example usage in your API
def handle_api_request(request_id: str, endpoint: str, user_data: dict):
    with start_flow(request_id, endpoint) as flow_id:
        print(f"Started flow: {flow_id}")
        result = register_user(user_data)
        return result

# Test it
if __name__ == "__main__":
    user_data = {"email": "test@example.com", "name": "John Doe"}
    result = handle_api_request("req_123", "/api/register", user_data)
    print(f"Registration complete: {result}")