import logging
import aiohttp
import asyncio
from typing import Dict, Any
from fastapi import Request, HTTPException
from app.pubsub.client import PubSubClient
from app.pubsub.utils import parse_pubsub_message

logger = logging.getLogger(__name__)

class PracticeDeliveryWebhook:
    """Webhook handler for delivering practice pronunciation results to frontend"""
    
    def __init__(self):
        self.pubsub_client = PubSubClient()
        
    async def send_webhook_to_frontend(self, webhook_url: str, payload: Dict[str, Any]) -> bool:
        """Send webhook to frontend with the pronunciation results
        
        Args:
            webhook_url: URL to send the webhook to
            payload: The data to send
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    webhook_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "IELTS-Practice-Pronunciation-Service/1.0"
                    }
                ) as response:
                    if response.status == 200:
                        logger.info(f"✅ Successfully sent webhook to {webhook_url}")
                        return True
                    else:
                        logger.warning(f"⚠️ Webhook returned status {response.status}: {await response.text()}")
                        return False
                        
        except asyncio.TimeoutError:
            logger.error(f"❌ Webhook timeout to {webhook_url}")
            return False
        except Exception as e:
            logger.error(f"❌ Error sending webhook to {webhook_url}: {str(e)}")
            return False
            
    async def process_delivery(self, message_data: Dict[str, Any]) -> None:
        """Process delivery of practice pronunciation results"""
        try:
            request_id = message_data.get("request_id")
            user_id = message_data.get("user_id")
            status = message_data.get("status")
            result = message_data.get("result")
            webhook_url = message_data.get("webhook_url")
            error = message_data.get("error")
            
            if not request_id or not webhook_url:
                logger.error("Missing required fields in delivery message")
                return
                
            logger.info(f"🚀 Delivering practice pronunciation result for request: {request_id}")
            
            # Prepare webhook payload
            webhook_payload = {
                "event": "practice_pronunciation_complete",
                "request_id": request_id,
                "user_id": user_id,
                "status": status,
                "timestamp": message_data.get("timestamp"),
                "data": result if status == "completed" else None,
                "error": error if status == "failed" else None
            }
            
            # Send webhook to frontend
            success = await self.send_webhook_to_frontend(webhook_url, webhook_payload)
            
            if success:
                logger.info(f"✅ Successfully delivered practice pronunciation result for request: {request_id}")
            else:
                logger.error(f"❌ Failed to deliver practice pronunciation result for request: {request_id}")
                
                # TODO: Implement retry logic here if needed
                # For now, just log the failure
                
        except Exception as e:
            logger.error(f"Error processing delivery: {str(e)}")
            
    async def handle_practice_delivery_webhook(self, request: Request) -> Dict[str, str]:
        """Handle practice pronunciation delivery webhook from Pub/Sub push
        
        Args:
            request: FastAPI Request object containing Pub/Sub push message
            
        Returns:
            Success response
        """
        try:
            # Parse the Pub/Sub message
            parsed_message = await parse_pubsub_message(request)
            message_data = parsed_message["data"]
            
            await self.process_delivery(message_data)
            
            return {"status": "success", "message": "Practice pronunciation delivery completed"}
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error handling practice delivery webhook: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}") 