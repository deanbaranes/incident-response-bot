from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@patch("core.settings.settings.USE_KAFKA_QUEUE", True)
@patch("api.webhook.producer", new_callable=AsyncMock)
@patch("api.webhook._verify_signature")
def test_producer_publish_success(mock_verify, mock_producer):
    """Test webhook successfully publishes to Kafka and returns 202."""
    mock_verify.return_value = True

    payload = {"alerts": [{"status": "firing", "labels": {"alertname": "TestAlert"}}]}

    response = client.post("/webhook", json=payload)

    assert response.status_code == 202
    assert response.json()["status"] == "processing"

    # Assert producer was called with correct topic and key
    mock_producer.send_and_wait.assert_called_once()
    kwargs = mock_producer.send_and_wait.call_args.kwargs
    assert kwargs["topic"] == "incident.webhooks"
    assert kwargs["key"] == b"TestAlert"


@patch("core.settings.settings.USE_KAFKA_QUEUE", True)
@patch("api.webhook.producer", new_callable=AsyncMock)
@patch("api.webhook._verify_signature")
def test_producer_broker_down(mock_verify, mock_producer):
    """Test webhook returns 503 if Kafka broker is down."""
    mock_verify.return_value = True
    mock_producer.send_and_wait.side_effect = Exception("Broker down")

    payload = {"alerts": [{"status": "firing", "labels": {"alertname": "TestAlert"}}]}

    response = client.post("/webhook", json=payload)

    # Expect 503 Service Unavailable since Kafka failed
    assert response.status_code == 503
    assert response.json()["detail"] == "Service Unavailable (Broker Down)"


@patch("core.settings.settings.USE_KAFKA_QUEUE", False)
@patch("api.webhook.producer", new_callable=AsyncMock)
@patch("api.webhook.process_incident")
@patch("api.webhook._verify_signature")
def test_producer_fallback_flag_false(
    mock_verify, mock_process_incident, mock_producer
):
    """Test webhook falls back to inline background task when USE_KAFKA_QUEUE is False."""
    mock_verify.return_value = True

    payload = {
        "alerts": [{"status": "firing", "labels": {"alertname": "FallbackAlert"}}]
    }

    response = client.post("/webhook", json=payload)

    assert response.status_code == 202

    # Producer should NOT be called
    mock_producer.send_and_wait.assert_not_called()

    # It shouldn't crash, the background task handles it (not easily assertable without mocking FastAPI background tasks directly, but we assert 202)


@patch("core.settings.settings.USE_KAFKA_QUEUE", True)
@patch("api.webhook.producer", None)
@patch("api.webhook.process_incident")
@patch("api.webhook._verify_signature")
def test_producer_fallback_producer_none(mock_verify, mock_process_incident):
    """Test webhook falls back gracefully if Kafka producer failed to initialize (is None)."""
    mock_verify.return_value = True

    payload = {
        "alerts": [{"status": "firing", "labels": {"alertname": "NoneProducerAlert"}}]
    }

    response = client.post("/webhook", json=payload)

    # Should not crash with NullPointer/AttributeError on None, should return 202
    assert response.status_code == 202


@patch("api.webhook._verify_signature")
def test_producer_payload_too_large(mock_verify):
    """Test webhook rejects payloads exceeding the 1MB limit (DOS Protection)."""
    mock_verify.return_value = True

    # Simulate headers of a 2MB payload
    headers = {"content-length": str(2 * 1024 * 1024)}
    payload = {"alerts": [{"status": "firing"}]}

    response = client.post("/webhook", json=payload, headers=headers)

    # Expect 413 Payload Too Large
    assert response.status_code == 413


@patch("core.settings.settings.USE_KAFKA_QUEUE", True)
@patch("api.webhook.producer", new_callable=AsyncMock)
@patch("api.webhook._verify_signature")
def test_producer_missing_alertname(mock_verify, mock_producer):
    """Test webhook handles missing alertname gracefully by defaulting to 'unknown' key."""
    mock_verify.return_value = True

    # Valid payload but missing 'labels' or 'alertname'
    payload = {"alerts": [{"status": "firing"}]}

    response = client.post("/webhook", json=payload)

    assert response.status_code == 202

    mock_producer.send_and_wait.assert_called_once()
    kwargs = mock_producer.send_and_wait.call_args.kwargs
    assert kwargs["topic"] == "incident.webhooks"
    # The default key should be 'unknown'
    assert kwargs["key"] == b"unknown"
