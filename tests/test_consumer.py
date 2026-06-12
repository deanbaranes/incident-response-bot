import pytest
import json
from unittest.mock import patch, AsyncMock
from workers.incident_consumer import send_to_dlq, consume


class MockMsg:
    def __init__(self, value: bytes, partition: int = 0, offset: int = 0):
        self.value = value
        self.partition = partition
        self.offset = offset


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


class FakeConsumer:
    def __init__(self, messages):
        self.messages = messages
        self.commit = AsyncMock()
        self.start = AsyncMock()
        self.stop = AsyncMock()

    async def __aiter__(self):
        for msg in self.messages:
            yield msg


@pytest.mark.asyncio
@patch("core.settings.settings.USE_KAFKA_QUEUE", True)
@patch("workers.incident_consumer.AIOKafkaProducer")
@patch("workers.incident_consumer.AIOKafkaConsumer")
@patch("workers.incident_consumer.process_incident", new_callable=AsyncMock)
@patch("workers.incident_consumer.start_http_server")
@patch("workers.incident_consumer.init_db", new_callable=AsyncMock)
@patch("workers.incident_consumer.is_incident_processed", new_callable=AsyncMock)
@patch("workers.incident_consumer.mark_incident_processed", new_callable=AsyncMock)
async def test_consume_success(
    mock_mark,
    mock_is_processed,
    mock_init,
    mock_start_http_server,
    mock_process_incident,
    mock_consumer_cls,
    mock_producer_cls,
):
    """Test successful message processing and offset commit."""
    mock_consumer = AsyncMock()
    mock_consumer_cls.return_value = mock_consumer
    mock_producer = AsyncMock()
    mock_producer_cls.return_value = mock_producer
    mock_is_processed.return_value = False

    # Provide one valid message
    msg_value = json.dumps({"incident_id": "test-1", "alert": "HighCPU"}).encode(
        "utf-8"
    )
    mock_consumer = FakeConsumer([MockMsg(msg_value)])
    mock_consumer_cls.return_value = mock_consumer

    await consume()

    # Assert db initialized
    mock_init.assert_called_once()

    # Assert process_incident was called with the correct payload
    mock_process_incident.assert_called_once_with(
        {"incident_id": "test-1", "alert": "HighCPU"}, "test-1"
    )

    # Assert commit was called
    mock_consumer.commit.assert_called_once()

    # Assert incident is added to idempotency cache
    mock_mark.assert_called_once_with("test-1")


@pytest.mark.asyncio
@patch("core.settings.settings.USE_KAFKA_QUEUE", True)
@patch("workers.incident_consumer.AIOKafkaProducer")
@patch("workers.incident_consumer.AIOKafkaConsumer")
@patch("workers.incident_consumer.process_incident", new_callable=AsyncMock)
@patch("workers.incident_consumer.start_http_server")
@patch("workers.incident_consumer.init_db", new_callable=AsyncMock)
@patch("workers.incident_consumer.is_incident_processed", new_callable=AsyncMock)
@patch("workers.incident_consumer.mark_incident_processed", new_callable=AsyncMock)
async def test_consume_exception_routes_to_dlq(
    mock_mark,
    mock_is_processed,
    mock_init,
    mock_start_http_server,
    mock_process_incident,
    mock_consumer_cls,
    mock_producer_cls,
):
    """Test that a processing error routes the message to DLQ and still commits."""
    mock_consumer = AsyncMock()
    mock_consumer_cls.return_value = mock_consumer
    mock_producer = AsyncMock()
    mock_producer_cls.return_value = mock_producer
    mock_is_processed.return_value = False

    # Make process_incident throw an exception
    mock_process_incident.side_effect = Exception("AI failed")

    msg_value = json.dumps({"incident_id": "test-error"}).encode("utf-8")
    mock_consumer = FakeConsumer([MockMsg(msg_value)])
    mock_consumer_cls.return_value = mock_consumer

    await consume()

    # Verify DLQ producer was called
    mock_producer.send_and_wait.assert_called_once()
    kwargs = mock_producer.send_and_wait.call_args.kwargs
    assert kwargs["topic"] == "incident.webhooks.dlq"
    assert kwargs["value"] == msg_value
    assert kwargs["headers"] == [("error", b"AI failed")]

    # Verify that we STILL commit the offset to prevent infinite loop
    mock_consumer.commit.assert_called_once()

    # Verify it was NOT added to the cache, so it can be retried later if re-inserted
    mock_mark.assert_not_called()


@pytest.mark.asyncio
@patch("core.settings.settings.USE_KAFKA_QUEUE", True)
@patch("workers.incident_consumer.AIOKafkaProducer")
@patch("workers.incident_consumer.AIOKafkaConsumer")
@patch("workers.incident_consumer.process_incident", new_callable=AsyncMock)
@patch("workers.incident_consumer.start_http_server")
@patch("workers.incident_consumer.init_db", new_callable=AsyncMock)
@patch("workers.incident_consumer.is_incident_processed", new_callable=AsyncMock)
@patch("workers.incident_consumer.mark_incident_processed", new_callable=AsyncMock)
async def test_consume_idempotency_skips_duplicate(
    mock_mark,
    mock_is_processed,
    mock_init,
    mock_start_http_server,
    mock_process_incident,
    mock_consumer_cls,
    mock_producer_cls,
):
    """Test that duplicate incident_ids are skipped but offset is committed."""
    mock_consumer = AsyncMock()
    mock_consumer_cls.return_value = mock_consumer
    mock_producer = AsyncMock()
    mock_producer_cls.return_value = mock_producer

    # First time not processed, second time processed
    mock_is_processed.side_effect = [False, True]

    msg_value = json.dumps({"incident_id": "test-dup"}).encode("utf-8")

    # Send the exact same message TWICE
    mock_consumer = FakeConsumer(
        [MockMsg(msg_value, offset=1), MockMsg(msg_value, offset=2)]
    )
    mock_consumer_cls.return_value = mock_consumer

    await consume()

    # process_incident should only be called ONCE
    mock_process_incident.assert_called_once()

    # But commit should be called TWICE (once for the successful process, once for the skipped dup)
    assert mock_consumer.commit.call_count == 2
    mock_mark.assert_called_once()


@pytest.mark.asyncio
@patch("core.settings.settings.USE_KAFKA_QUEUE", True)
@patch("workers.incident_consumer.AIOKafkaProducer")
@patch("workers.incident_consumer.AIOKafkaConsumer")
@patch("workers.incident_consumer.process_incident", new_callable=AsyncMock)
@patch("workers.incident_consumer.start_http_server")
@patch("workers.incident_consumer.init_db", new_callable=AsyncMock)
@patch("workers.incident_consumer.is_incident_processed", new_callable=AsyncMock)
@patch("workers.incident_consumer.mark_incident_processed", new_callable=AsyncMock)
async def test_consume_missing_incident_id(
    mock_mark,
    mock_is_processed,
    mock_init,
    mock_start_http_server,
    mock_process_incident,
    mock_consumer_cls,
    mock_producer_cls,
):
    """Test message without incident_id processes normally but doesn't cache."""
    mock_consumer = AsyncMock()
    mock_consumer_cls.return_value = mock_consumer
    mock_producer = AsyncMock()
    mock_producer_cls.return_value = mock_producer

    # Missing incident_id
    msg_value = json.dumps({"alert": "NoID"}).encode("utf-8")
    mock_consumer = FakeConsumer([MockMsg(msg_value)])
    mock_consumer_cls.return_value = mock_consumer

    await consume()

    # Should still process and commit
    mock_process_incident.assert_called_once_with({"alert": "NoID"}, None)
    mock_consumer.commit.assert_called_once()
    mock_is_processed.assert_not_called()
    mock_mark.assert_not_called()
