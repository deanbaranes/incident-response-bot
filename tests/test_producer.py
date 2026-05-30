from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@patch("api.webhook.USE_KAFKA_QUEUE", True)
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


@patch("api.webhook.USE_KAFKA_QUEUE", True)
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
