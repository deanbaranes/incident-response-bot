import pytest
import importlib
import config
from unittest.mock import patch


@patch("config.load_dotenv")
def test_missing_required_env_vars(mock_load):
    """Test that missing required environment variables raises RuntimeError."""

    def mock_getenv(name, default=None):
        if name == "WEBHOOK_SECRET":
            return None
        if name == "EMAIL_PORT":
            return "587"
        return "dummy_value"

    with patch("os.getenv", side_effect=mock_getenv):
        with pytest.raises(
            RuntimeError,
            match="Missing required environment variables:.*WEBHOOK_SECRET",
        ):
            importlib.reload(config)


@patch("config.load_dotenv")
def test_all_required_env_vars_present(mock_load):
    """Test that app starts successfully when all variables are present."""

    def mock_getenv(name, default=None):
        if name == "EMAIL_PORT":
            return "587"
        return "dummy_value"

    with patch("os.getenv", side_effect=mock_getenv):
        reloaded_config = importlib.reload(config)
        assert reloaded_config.WEBHOOK_SECRET == "dummy_value"
