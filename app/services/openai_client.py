import aiohttp
import logging
from typing import Optional
from app.core.config import OPENAI_API_KEY, OPENAI_API_URL

logger = logging.getLogger(__name__)

# Shared client instance
_client: Optional['OpenAIClient'] = None


class OpenAIClient:
    """Shared OpenAI HTTP client with connection pooling"""

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    def _get_session(self) -> aiohttp.ClientSession:
        """Lazily create session on first use (must be called from async context)"""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=20,  # Max 20 concurrent connections
                ttl_dns_cache=300,  # Cache DNS for 5 minutes
                keepalive_timeout=30,  # Keep connections alive for 30 seconds
            )
            timeout = aiohttp.ClientTimeout(total=60, connect=10)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {OPENAI_API_KEY}"
                }
            )
        return self._session

    async def chat(self, model: str, messages: list, **kwargs) -> dict:
        """Make a chat completion request"""
        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }

        session = self._get_session()
        async with session.post(OPENAI_API_URL, json=payload) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                logger.error(f"OpenAI API error {response.status}: {error_text[:200]}")
                raise Exception(f"OpenAI API error: {response.status}")

    async def close(self):
        """Close the client session"""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None


def get_openai_client() -> OpenAIClient:
    """Get the shared OpenAI client instance"""
    global _client
    if _client is None:
        _client = OpenAIClient()
    return _client


async def close_openai_client():
    """Close the shared client (call on app shutdown)"""
    global _client
    if _client:
        await _client.close()
        _client = None
