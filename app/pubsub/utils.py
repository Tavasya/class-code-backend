import base64
import json
import logging
import time
from typing import Dict, Any, Optional, Set
from fastapi import Request, HTTPException
from functools import wraps

logger = logging.getLogger(__name__)

# In-memory cache for processed message IDs
processed_messages: Dict[str, float] = {}
CACHE_EXPIRY = 3600  # 1 hour in seconds

def is_duplicate_message(message_id: str) -> bool:
    """
    Check if a message has been processed recently.
    Also cleans up old message IDs from the cache.
    """
    current_time = time.time()
    
    # Clean up old messages
    expired_ids = [msg_id for msg_id, timestamp in processed_messages.items() 
                  if current_time - timestamp > CACHE_EXPIRY]
    for msg_id in expired_ids:
        del processed_messages[msg_id]
    
    # Check if message is duplicate
    if message_id in processed_messages:
        return True
    
    # Add message to cache
    processed_messages[message_id] = current_time
    return False

async def parse_pubsub_message(request: Request) -> Dict[str, Any]:
    """
    Parse a Pub/Sub push message from the request.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Parsed message data
        
    Raises:
        HTTPException: If message format is invalid
    """
    try:
        body = await request.json()
        
        if "message" not in body:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format: missing 'message' field")
        
        message = body["message"]
        
        if "data" not in message:
            raise HTTPException(status_code=400, detail="Invalid Pub/Sub message format: missing 'data' field")
        
        # Decode base64 data
        try:
            decoded_data = base64.b64decode(message["data"]).decode("utf-8")
            message_data = json.loads(decoded_data)
        except (base64.binascii.Error, json.JSONDecodeError) as e:
            logger.error(f"Failed to decode Pub/Sub message data: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid message data format: {str(e)}")
        
        return {
            "data": message_data,
            "attributes": message.get("attributes", {}),
            "message_id": message.get("messageId", ""),
            "publish_time": message.get("publishTime", "")
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse request body as JSON: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")
    except Exception as e:
        logger.error(f"Unexpected error parsing Pub/Sub message: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal error processing message")

def verify_pubsub_token(request: Request, expected_token: Optional[str] = None) -> bool:
    """
    Verify Pub/Sub push authentication token.
    
    Args:
        request: FastAPI Request object
        expected_token: Expected authentication token (optional)
        
    Returns:
        True if token is valid or no verification is required
    """
    if not expected_token:
        return True
    
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    
    token = auth_header[7:]  # Remove "Bearer " prefix
    return token == expected_token

def safe_webhook_handler(handler_func):
    """
    Decorator to safely handle webhook calls with deduplication and error handling.
    Prevents infinite loops by always returning success even on processing errors.
    """
    @wraps(handler_func)
    async def wrapper(request: Request):
        try:
            # Parse message first to get message ID
            parsed_message = await parse_pubsub_message(request)
            message_id = parsed_message["message_id"]
            
            # Check for duplicate messages
            if is_duplicate_message(message_id):
                logger.warning(f"Duplicate message detected and ignored: {message_id}")
                return {"status": "success", "message": "Duplicate message ignored"}
            
            # Call the actual handler by reconstructing the original request
            logger.info(f"Processing message: {message_id}")
            result = await handler_func(request)
            logger.info(f"Successfully processed message: {message_id}")
            return result
            
        except HTTPException as e:
            # Return success to prevent PubSub retries, but log the error
            logger.error(f"HTTPException in webhook handler: {e.detail}")
            return {"status": "error_acknowledged", "message": f"Error processed: {e.detail}"}
            
        except Exception as e:
            # Return success to prevent PubSub retries, but log the error
            logger.error(f"Exception in webhook handler: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {"status": "error_acknowledged", "message": f"Error processed: {str(e)}"}
    
    return wrapper 