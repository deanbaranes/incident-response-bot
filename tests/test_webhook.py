import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


def _make_client():
    with patch("services.ai.genai"):
        import importlib
        import main as main_mod
        importlib.reload(main_mod)
        return TestClient(main_mod.app, raise_server_exceptions=False)


def _sign(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


VALID_PAYLOAD = json.dumps({
    "alerts": [
        {
            "status": "firing",
            "labels": {"alertname": "HighCPUUsage"},
            "annotations": {"summary": "CPU at 90%"},
        }
    ]
}).encode()


class TestWebhookSignatureVerification:
    def test_valid_signature_accepted(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "mysecret")
        with patch("api.webhook.WEBHOOK_SECRET", "mysecret"):
            with patch("core.engine.process_incident"):
                client = _make_client()
                sig = _sign(VALID_PAYLOAD, "mysecret")
                resp = client.post(
                    "/webhook",
                    content=VALID_PAYLOAD,
                    headers={"Content-Type": "application/json",
                             "X-Grafana-Webhook-Signature": sig},
                )
                assert resp.status_code == 200

    def test_invalid_signature_returns_401(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "mysecret")
        with patch("api.webhook.WEBHOOK_SECRET", "mysecret"):
            client = _make_client()
            resp = client.post(
                "/webhook",
                content=VALID_PAYLOAD,
                headers={"Content-Type": "application/json",
                         "X-Grafana-Webhook-Signature": "sha256=badhash"},
            )
            assert resp.status_code == 401

    def test_missing_signature_returns_401_when_secret_set(self, monkeypatch):
        monkeypatch.setenv("WEBHOOK_SECRET", "mysecret")
        with patch("api.webhook.WEBHOOK_SECRET", "mysecret"):
            client = _make_client()
            resp = client.post(
                "/webhook",
                content=VALID_PAYLOAD,
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 401

    def test_no_secret_set_skips_verification(self, monkeypatch):
        monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
        with patch("api.webhook.WEBHOOK_SECRET", ""):
            with patch("core.engine.process_incident"):
                client = _make_client()
                resp = client.post(
                    "/webhook",
                    content=VALID_PAYLOAD,
                    headers={"Content-Type": "application/json"},
                )
                assert resp.status_code == 200


class TestWebhookPayloadValidation:
    def test_empty_alerts_returns_422(self):
        with patch("api.webhook.WEBHOOK_SECRET", ""):
            client = _make_client()
            resp = client.post(
                "/webhook",
                json={"alerts": []},
            )
            assert resp.status_code == 422

    def test_missing_alerts_key_returns_422(self):
        with patch("api.webhook.WEBHOOK_SECRET", ""):
            client = _make_client()
            resp = client.post("/webhook", json={"foo": "bar"})
            assert resp.status_code == 422

    def test_malformed_json_returns_422(self):
        with patch("api.webhook.WEBHOOK_SECRET", ""):
            client = _make_client()
            resp = client.post(
                "/webhook",
                content=b"not json at all",
                headers={"Content-Type": "application/json"},
            )
            assert resp.status_code == 422

    def test_valid_payload_returns_processing(self):
        with patch("api.webhook.WEBHOOK_SECRET", ""):
            with patch("core.engine.process_incident"):
                client = _make_client()
                resp = client.post("/webhook", json=json.loads(VALID_PAYLOAD))
                assert resp.status_code == 200
                assert resp.json() == {"status": "processing"}
