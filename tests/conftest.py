import os
import sys
import json
import pytest
import yaml
from unittest.mock import MagicMock

# ── Set dummy env vars BEFORE any project module is imported ──────────────────
# config.py raises RuntimeError on missing required vars — this prevents that.
_DUMMY_ENV = {
    "GITHUB_TOKEN": "ghp_test_dummy",
    "GITHUB_REPO": "test-org/test-repo",
    "GEMINI_API_KEY": "AIza_test_dummy",
    "EMAIL_SENDER": "test@example.com",
    "EMAIL_PASSWORD": "test_password",
    "GRAFANA_TOKEN": "glsa_test_dummy",
    "GRAFANA_URL": "http://localhost:3000",
    "GRAFANA_USERNAME": "",
    "GRAFANA_DASHBOARD_URL": "http://localhost:3000/d/test/dashboard",
    "EMAIL_RECIPIENTS": "",
    "WEBHOOK_SECRET": "",
}
for key, value in _DUMMY_ENV.items():
    os.environ.setdefault(key, value)

# ── Stub out heavy third-party libs so tests don't need them installed ────────
# google-generativeai makes network calls at import time.
_genai_mock = MagicMock()
_genai_mock.GenerativeModel.return_value = MagicMock()
sys.modules.setdefault("google", MagicMock())
sys.modules.setdefault("google.generativeai", _genai_mock)
sys.modules.setdefault("PIL", MagicMock())
sys.modules.setdefault("PIL.Image", MagicMock())

# playwright isn't installed in the test env — stub it out.
_pw_mock = MagicMock()
sys.modules.setdefault("playwright", _pw_mock)
sys.modules.setdefault("playwright.sync_api", _pw_mock)


# ── Fixtures ──────────────────────────────────────────────────────────────────
@pytest.fixture
def grafana_webhook_payload():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    with open(os.path.join(fixtures_dir, "grafana_webhook.json")) as f:
        return json.load(f)


@pytest.fixture
def sample_playbook():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    with open(os.path.join(fixtures_dir, "playbook_high_cpu.yaml")) as f:
        return yaml.safe_load(f)


@pytest.fixture
def firing_alert():
    return {
        "status": "firing",
        "labels": {"alertname": "HighCPUUsage", "instance": "node-01"},
        "annotations": {"summary": "CPU at 94%"},
    }
