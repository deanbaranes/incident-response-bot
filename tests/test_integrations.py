import pytest
import httpx
from unittest.mock import patch, Mock, AsyncMock

from services.grafana_oncall import send_grafana_oncall_alert
from services.opsgenie import send_opsgenie_alert
from services.pagerduty import create_pagerduty_incident


@pytest.fixture
def mock_httpx_post():
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        yield mock_post


@pytest.mark.asyncio
async def test_grafana_oncall_success(mock_httpx_post):
    with patch("core.settings.settings.GRAFANA_ONCALL_WEBHOOK_URL", "http://test"):
        mock_resp = Mock()
        mock_resp.raise_for_status.return_value = None
        mock_httpx_post.return_value = mock_resp

        result = await send_grafana_oncall_alert("test title", "test msg", "test_alert")
        assert result is True
        mock_httpx_post.assert_called_once()


@pytest.mark.asyncio
async def test_grafana_oncall_missing_url():
    with patch("core.settings.settings.GRAFANA_ONCALL_WEBHOOK_URL", None):
        with pytest.raises(
            RuntimeError, match="GRAFANA_ONCALL_WEBHOOK_URL is not configured"
        ):
            await send_grafana_oncall_alert("test", "test", "test")


@pytest.mark.asyncio
async def test_opsgenie_success(mock_httpx_post):
    with patch("core.settings.settings.OPSGENIE_API_KEY", "test-key"), patch(
        "core.settings.settings.OPSGENIE_REGION", "eu"
    ):
        mock_resp = Mock()
        mock_resp.raise_for_status.return_value = None
        mock_httpx_post.return_value = mock_resp

        result = await send_opsgenie_alert(
            "test title", "test msg", "test_alert", priority="P1"
        )
        assert result is True

        mock_httpx_post.assert_called_once()
        args, kwargs = mock_httpx_post.call_args
        assert args[0] == "https://api.eu.opsgenie.com/v2/alerts"
        assert kwargs["headers"]["Authorization"] == "GenieKey test-key"
        assert kwargs["headers"]["Content-Type"] == "application/json"
        assert kwargs["json"]["priority"] == "P1"


@pytest.mark.asyncio
async def test_opsgenie_retry_failure(mock_httpx_post):
    with patch("core.settings.settings.OPSGENIE_API_KEY", "test-key"):
        # Make it always raise RequestError
        mock_httpx_post.side_effect = httpx.RequestError(
            "Network Error", request=Mock()
        )

        with pytest.raises(httpx.RequestError):
            await send_opsgenie_alert("test title", "test msg", "test_alert")

        # Should have retried 3 times
        assert mock_httpx_post.call_count == 3


@pytest.mark.asyncio
async def test_pagerduty_success(mock_httpx_post):
    with patch("core.settings.settings.PAGERDUTY_ROUTING_KEY", "test-key"):
        mock_resp = Mock()
        mock_resp.raise_for_status.return_value = None
        mock_httpx_post.return_value = mock_resp

        result = await create_pagerduty_incident(
            "test title", "test msg", "test_alert", severity="warning"
        )
        assert result is True

        mock_httpx_post.assert_called_once()
        args, kwargs = mock_httpx_post.call_args
        assert args[0] == "https://events.pagerduty.com/v2/enqueue"
        assert kwargs["json"]["routing_key"] == "test-key"
        assert kwargs["json"]["payload"]["severity"] == "warning"
