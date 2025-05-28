import pytest
import base64
import json
from fastapi import HTTPException
from app.pubsub.utils import parse_pubsub_message


class TestMessageParsing:
    """Test Pub/Sub message parsing and validation - Cost: $0.00"""

    @pytest.mark.asyncio
    async def test_valid_pubsub_push_message_parsing(self, webhook_request_factory):
        """Test successful parsing of valid Pub/Sub push message"""
        # Create valid message data
        message_data = {
            "submission_url": "test-submission-123",
            "question_number": 1,
            "audio_url": "https://example.com/audio.webm"
        }
        
        # Encode as base64 (like real Pub/Sub does)
        json_data = json.dumps(message_data)
        base64_data = base64.b64encode(json_data.encode()).decode()
        
        # Create mock request
        mock_request = webhook_request_factory(base64_data)
        
        # Parse the message
        parsed_message = await parse_pubsub_message(mock_request)
        
        # Verify parsing worked correctly
        assert parsed_message is not None
        assert "data" in parsed_message
        assert "message_id" in parsed_message
        assert "publish_time" in parsed_message
        
        # Verify data was decoded correctly
        extracted_data = parsed_message["data"]
        assert extracted_data["submission_url"] == "test-submission-123"
        assert extracted_data["question_number"] == 1
        assert extracted_data["audio_url"] == "https://example.com/audio.webm"

    @pytest.mark.asyncio 
    async def test_malformed_base64_message_handling(self, webhook_request_factory):
        """Test handling of invalid base64 encoded message"""
        # Create invalid base64 data
        invalid_base64 = "invalid-base64-data!!!"
        
        # Create mock request with invalid data
        mock_request = webhook_request_factory(invalid_base64)
        
        # Should raise HTTPException for invalid base64
        with pytest.raises(HTTPException) as exc_info:
            await parse_pubsub_message(mock_request)
        
        assert exc_info.value.status_code == 500
        assert "Internal error processing message" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_invalid_json_message_handling(self, webhook_request_factory):
        """Test handling of valid base64 but invalid JSON"""
        # Create valid base64 but invalid JSON
        invalid_json = "{ invalid json structure"
        base64_data = base64.b64encode(invalid_json.encode()).decode()
        
        # Create mock request
        mock_request = webhook_request_factory(base64_data)
        
        # Should raise HTTPException for invalid JSON
        with pytest.raises(HTTPException) as exc_info:
            await parse_pubsub_message(mock_request)
        
        assert exc_info.value.status_code == 500
        assert "Internal error processing message" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_missing_message_field_handling(self):
        """Test handling of request missing 'message' field"""
        from unittest.mock import AsyncMock, Mock
        from fastapi import Request
        
        # Create request without 'message' field
        mock_request = Mock(spec=Request)
        mock_request.json = AsyncMock(return_value={"not_message": "data"})
        
        # Should raise HTTPException for missing message field
        with pytest.raises(HTTPException) as exc_info:
            await parse_pubsub_message(mock_request)
        
        assert exc_info.value.status_code == 500
        assert "Internal error processing message" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_missing_data_field_handling(self):
        """Test handling of message missing 'data' field"""
        from unittest.mock import AsyncMock, Mock
        from fastapi import Request
        
        # Create request with message but no data
        mock_request = Mock(spec=Request)
        mock_request.json = AsyncMock(return_value={
            "message": {
                "messageId": "test-id",
                "publishTime": "2024-01-01T12:00:00.000Z"
                # Missing 'data' field
            }
        })
        
        # Should raise HTTPException for missing data field
        with pytest.raises(HTTPException) as exc_info:
            await parse_pubsub_message(mock_request)
        
        assert exc_info.value.status_code == 500
        assert "Internal error processing message" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_message_attributes_extraction(self, webhook_request_factory):
        """Test proper extraction of message attributes and metadata"""
        # Create message with attributes
        message_data = {"test": "data"}
        json_data = json.dumps(message_data)
        base64_data = base64.b64encode(json_data.encode()).decode()
        
        # Create mock request with attributes
        attributes = {"source": "test", "version": "1.0"}
        mock_request = webhook_request_factory(base64_data, attributes)
        
        # Parse the message
        parsed_message = await parse_pubsub_message(mock_request)
        
        # Verify all fields are extracted
        assert parsed_message["data"]["test"] == "data"
        assert parsed_message["attributes"]["source"] == "test"
        assert parsed_message["attributes"]["version"] == "1.0"
        assert parsed_message["message_id"] == "mock-message-id-123"
        assert parsed_message["publish_time"] == "2024-01-01T12:00:00.000Z"

    @pytest.mark.asyncio
    async def test_empty_attributes_handling(self, webhook_request_factory):
        """Test handling of messages with no attributes"""
        message_data = {"test": "data"}
        json_data = json.dumps(message_data)
        base64_data = base64.b64encode(json_data.encode()).decode()
        
        # Create mock request without attributes
        mock_request = webhook_request_factory(base64_data)
        
        # Parse the message
        parsed_message = await parse_pubsub_message(mock_request)
        
        # Verify attributes default to empty dict
        assert parsed_message["attributes"] == {}
        assert parsed_message["data"]["test"] == "data"

    @pytest.mark.asyncio
    async def test_complex_message_data_parsing(self, webhook_request_factory):
        """Test parsing of complex nested message data"""
        # Create complex message data
        complex_data = {
            "submission_url": "complex-test-submission",
            "question_results": {
                "1": {
                    "pronunciation": {"grade": 85.5, "issues": []},
                    "grammar": {"grade": 78.2, "issues": [{"type": "error", "message": "test"}]}
                },
                "2": {
                    "pronunciation": {"grade": 90.0, "issues": []},
                    "grammar": {"grade": 82.5, "issues": []}
                }
            },
            "metadata": {
                "timestamp": "2024-01-01T12:00:00.000Z",
                "version": "1.0"
            }
        }
        
        # Encode and create request
        json_data = json.dumps(complex_data)
        base64_data = base64.b64encode(json_data.encode()).decode()
        mock_request = webhook_request_factory(base64_data)
        
        # Parse the message
        parsed_message = await parse_pubsub_message(mock_request)
        extracted_data = parsed_message["data"]
        
        # Verify complex structure is preserved
        assert extracted_data["submission_url"] == "complex-test-submission"
        assert "question_results" in extracted_data
        assert "1" in extracted_data["question_results"]
        assert "2" in extracted_data["question_results"]
        assert extracted_data["question_results"]["1"]["pronunciation"]["grade"] == 85.5
        assert extracted_data["question_results"]["2"]["grammar"]["grade"] == 82.5
        assert extracted_data["metadata"]["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_unicode_content_parsing(self, webhook_request_factory):
        """Test parsing of messages with unicode content"""
        # Create message with unicode content
        message_data = {
            "submission_url": "unicode-test",
            "transcript": "Bonjour, comment ça va? 你好世界 🌍",
            "feedback": "Très bien! 很好!"
        }
        
        # Encode and create request
        json_data = json.dumps(message_data, ensure_ascii=False)
        base64_data = base64.b64encode(json_data.encode('utf-8')).decode()
        mock_request = webhook_request_factory(base64_data)
        
        # Parse the message
        parsed_message = await parse_pubsub_message(mock_request)
        extracted_data = parsed_message["data"]
        
        # Verify unicode content is preserved
        assert extracted_data["transcript"] == "Bonjour, comment ça va? 你好世界 🌍"
        assert extracted_data["feedback"] == "Très bien! 很好!"

    @pytest.mark.asyncio
    async def test_large_message_parsing(self, webhook_request_factory):
        """Test parsing of large message data"""
        # Create large message data
        large_message = {
            "submission_url": "large-test-submission",
            "large_field": "x" * 10000,  # 10KB of data
            "question_results": {}
        }
        
        # Add many question results
        for i in range(50):
            large_message["question_results"][str(i)] = {
                "pronunciation": {"grade": 85.0 + i * 0.1, "issues": []},
                "grammar": {"grade": 78.0 + i * 0.1, "issues": []}
            }
        
        # Encode and create request
        json_data = json.dumps(large_message)
        base64_data = base64.b64encode(json_data.encode()).decode()
        mock_request = webhook_request_factory(base64_data)
        
        # Parse the message
        parsed_message = await parse_pubsub_message(mock_request)
        extracted_data = parsed_message["data"]
        
        # Verify large data is handled correctly
        assert extracted_data["submission_url"] == "large-test-submission"
        assert len(extracted_data["large_field"]) == 10000
        assert len(extracted_data["question_results"]) == 50
        assert extracted_data["question_results"]["49"]["pronunciation"]["grade"] == 89.9 