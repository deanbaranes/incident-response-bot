import pytest
import json
from unittest.mock import AsyncMock
from workers.incident_consumer import send_to_dlq


@pytest.mark.asyncio
async def test_send_to_dlq_valid_json():
    """Test DLQ producer successfully parses JSON and injects error."""
    mock_producer = AsyncMock()
    original_msg = json.dumps({"incident_id": "123"}).encode("utf-8")

    await send_to_dlq(mock_producer, original_msg, "Test error")

    mock_producer.send_and_wait.assert_called_once()
    kwargs = mock_producer.send_and_wait.call_args.kwargs
    assert kwargs["topic"] == "incident.webhooks.dlq"

    sent_payload = json.loads(kwargs["value"].decode("utf-8"))
    assert sent_payload["incident_id"] == "123"
    assert sent_payload["_dlq_error"] == "Test error"


@pytest.mark.asyncio
async def test_send_to_dlq_invalid_json():
    """Test DLQ producer falls back to raw bytes if message is not JSON."""
    mock_producer = AsyncMock()
    bad_msg = b"NOT_JSON"

    await send_to_dlq(mock_producer, bad_msg, "JSON Decode failed")

    mock_producer.send_and_wait.assert_called_once()
    kwargs = mock_producer.send_and_wait.call_args.kwargs
    assert kwargs["topic"] == "incident.webhooks.dlq"
    assert kwargs["value"] == b"NOT_JSON"
