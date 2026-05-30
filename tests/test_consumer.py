import pytest
from unittest.mock import AsyncMock
from workers.incident_consumer import send_to_dlq


@pytest.mark.asyncio
async def test_send_to_dlq_with_headers():
    """Test DLQ producer sends the original message and injects error in headers."""
    mock_producer = AsyncMock()
    original_msg = b'{"incident_id": "123"}'

    await send_to_dlq(mock_producer, original_msg, "Test error")

    mock_producer.send_and_wait.assert_called_once()
    kwargs = mock_producer.send_and_wait.call_args.kwargs
    assert kwargs["topic"] == "incident.webhooks.dlq"
    assert kwargs["value"] == original_msg
    assert kwargs["headers"] == [("error", b"Test error")]
