from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_webhook_valid_payload():
    """Test that a valid payload returns 200 processing."""
    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "HighCPUUsage"},
                "annotations": {"summary": "CPU over 90%"},
            }
        ]
    }
    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "processing"}


def test_webhook_invalid_payload():
    """Test that a malformed payload returns 422 Unprocessable Entity."""
    payload = {"wrong_key": "data"}
    response = client.post("/webhook", json=payload)
    assert response.status_code == 422
