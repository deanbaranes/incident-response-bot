import pytest
from unittest.mock import patch, AsyncMock
from core.context import IncidentContext
from core.actions.handlers.grafana import (
    CaptureDashboardHandler,
    FetchMetricsHandler,
    GrafanaQueryHandler,
)


@pytest.fixture
def dummy_context():
    ctx = IncidentContext(alert_name="TestAlert")
    ctx.summary = "Test Summary"
    ctx.enriched_data = ["log1", "log2"]
    ctx.ai_output = "Fix it"
    return ctx


@pytest.mark.asyncio
async def test_capture_dashboard_handler(dummy_context):
    handler = CaptureDashboardHandler()
    action = {"type": "capture_dashboard_screenshot", "url": "http://test-dash"}

    with patch("core.actions.handlers.grafana.capture_dashboard") as mock_capture:
        mock_capture.return_value = "fake_path.png"
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = "fake_path.png"
            await handler.execute(action, dummy_context, {})

            mock_thread.assert_called_once()
            assert "fake_path.png" in dummy_context.screenshots
            assert any(
                "Dashboard captured" in step for step in dummy_context.execution_steps
            )


@pytest.mark.asyncio
async def test_fetch_metrics_handler(dummy_context):
    handler = FetchMetricsHandler()
    action = {"type": "fetch_metrics", "target": "CPU", "query": "avg(cpu)"}

    with patch("core.actions.handlers.grafana.fetch_grafana_metric"):
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = "99.9%"
            await handler.execute(action, dummy_context, {})

            mock_thread.assert_called_once()
            assert any("99.9%" in data for data in dummy_context.enriched_data)
            assert any(
                "CPU metrics retrieved" in step
                for step in dummy_context.execution_steps
            )


@pytest.mark.asyncio
async def test_grafana_query_handler(dummy_context):
    handler = GrafanaQueryHandler()
    action = {
        "type": "grafana_query",
        "datasource_uid": "test_uid",
        "query": "test_query",
    }

    with patch("core.actions.handlers.grafana.execute_grafana_query"):
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.return_value = "Columns: A, B\n1, 2"
            await handler.execute(action, dummy_context, {})

            mock_thread.assert_called_once()
            assert any("Columns: A, B" in data for data in dummy_context.enriched_data)
            assert any(
                "Grafana generic query executed" in step
                for step in dummy_context.execution_steps
            )
