import pytest
from pydantic import ValidationError
import os
from unittest.mock import patch
from core.settings import Settings


def test_missing_required_env_vars():
    """Test that missing required environment variables raises ValidationError via pydantic."""
    with patch.dict(os.environ, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings(_env_file=None)

        error_msg = str(exc_info.value)
        assert "GEMINI_API_KEY" in error_msg
        assert "WEBHOOK_SECRET" in error_msg


def test_all_required_env_vars_present():
    """Test that Settings instantiates successfully when variables are present."""
    env_vars = {
        "GEMINI_API_KEY": "dummy",
        "WEBHOOK_SECRET": "dummy",
        "EMAIL_SENDER": "dummy@test.com",
        "EMAIL_PASSWORD": "dummy",
        "GRAFANA_URL": "http://grafana",
        "GRAFANA_TOKEN": "token",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        s = Settings(_env_file=None)
        assert s.GEMINI_API_KEY == "dummy"
        assert s.WEBHOOK_SECRET == "dummy"
        assert s.EMAIL_PORT == 587  # Default value
