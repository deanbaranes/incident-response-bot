import hmac
import hashlib
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

DUMMY_SECRET = "dummy_secret_for_testing"


def generate_signature(body_bytes: bytes, secret: str = DUMMY_SECRET) -> str:
    """Helper to generate valid HMAC signature for tests."""
    sig = hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    return "sha256=" + sig


@patch("api.webhook.WEBHOOK_SECRET", DUMMY_SECRET)
@patch("api.webhook.process_incident")
def test_webhook_valid_payload(mock_process):
    payload_bytes = json.dumps(
        {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "HighCPUUsage"},
                    "annotations": {"summary": "CPU over 90%"},
                }
            ]
        }
    ).encode("utf-8")

    headers = {
        "X-Grafana-Webhook-Signature": generate_signature(payload_bytes),
        "Content-Type": "application/json",
    }

    response = client.post("/webhook", content=payload_bytes, headers=headers)
    assert response.status_code == 200


@patch("api.webhook.WEBHOOK_SECRET", DUMMY_SECRET)
def test_webhook_invalid_signature():
    payload_bytes = json.dumps(
        {"alerts": [{"status": "firing", "labels": {"alertname": "HighCPUUsage"}}]}
    ).encode("utf-8")

    headers = {
        "X-Grafana-Webhook-Signature": "sha256=invalid1234567890abcdef",
        "Content-Type": "application/json",
    }

    response = client.post("/webhook", content=payload_bytes, headers=headers)
    assert response.status_code == 401


@patch("api.webhook.WEBHOOK_SECRET", DUMMY_SECRET)
def test_webhook_missing_signature():
    payload_bytes = b'{"alerts":[{"status":"firing"}]}'
    headers = {"Content-Type": "application/json"}
    response = client.post("/webhook", content=payload_bytes, headers=headers)
    assert response.status_code == 401


@patch("api.webhook.WEBHOOK_SECRET", DUMMY_SECRET)
def test_webhook_invalid_payload():
    payload_bytes = json.dumps({"wrong_key": "data"}).encode("utf-8")

    headers = {
        "X-Grafana-Webhook-Signature": generate_signature(payload_bytes),
        "Content-Type": "application/json",
    }

    response = client.post("/webhook", content=payload_bytes, headers=headers)
    assert response.status_code == 422
