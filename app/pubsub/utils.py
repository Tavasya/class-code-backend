import base64
import json
import logging
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

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