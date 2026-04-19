import math
import pytest
from unittest.mock import patch, MagicMock


def _mock_prom_response(value):
    """Build a mock requests.Response for a Prometheus instant query."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    if value is None:
        mock_resp.json.return_value = {"data": {"result": []}}
    else:
        mock_resp.json.return_value = {
            "data": {"result": [{"value": [1700000000, str(value)]}]}
        }
    return mock_resp


def _make_playwright_stack():
    """Return (context_manager, page_mock) for mocking sync_playwright()."""
    page = MagicMock()
    ctx = MagicMock()
    ctx.new_page.return_value = page
    browser = MagicMock()
    browser.new_context.return_value = ctx
    pw = MagicMock()
    pw.chromium.launch.return_value = browser
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=pw)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, page


class TestFetchGrafanaMetric:
    def test_empty_result_returns_no_data_message(self):
        with patch("services.grafana.requests.get", return_value=_mock_prom_response(None)), \
             patch("services.grafana.GRAFANA_URL", "http://localhost:3000"):
            from services.grafana import fetch_grafana_metric
            result = fetch_grafana_metric("CPU", "some_query")
            assert "No active data points" in result

    def test_valid_float_formatted_as_percentage(self):
        with patch("services.grafana.requests.get", return_value=_mock_prom_response(87.5432)), \
             patch("services.grafana.GRAFANA_URL", "http://localhost:3000"):
            from services.grafana import fetch_grafana_metric
            result = fetch_grafana_metric("CPU", "some_query")
            assert result == "87.5%"

    def test_nan_string_returns_na(self):
        with patch("services.grafana.requests.get", return_value=_mock_prom_response("NaN")), \
             patch("services.grafana.GRAFANA_URL", "http://localhost:3000"):
            from services.grafana import fetch_grafana_metric
            result = fetch_grafana_metric("CPU", "some_query")
            assert "N/A" in result

    def test_inf_value_returns_na(self):
        with patch("services.grafana.requests.get", return_value=_mock_prom_response(math.inf)), \
             patch("services.grafana.GRAFANA_URL", "http://localhost:3000"):
            from services.grafana import fetch_grafana_metric
            result = fetch_grafana_metric("CPU", "some_query")
            assert "N/A" in result

    def test_long_time_range_blocked(self):
        with patch("services.grafana.requests.get") as mock_get, \
             patch("services.grafana.GRAFANA_URL", "http://localhost:3000"):
            from services.grafana import fetch_grafana_metric
            result = fetch_grafana_metric("CPU", "rate(metric[30d])")
            mock_get.assert_not_called()
            assert "Blocked" in result

    def test_semicolon_stripped_from_query(self):
        with patch("services.grafana.requests.get", return_value=_mock_prom_response(50.0)) as mock_get, \
             patch("services.grafana.GRAFANA_URL", "http://localhost:3000"):
            from services.grafana import fetch_grafana_metric
            fetch_grafana_metric("CPU", "some_query; DROP TABLE alerts")
            params = mock_get.call_args[1]["params"]
            assert ";" not in params["query"]

    def test_missing_grafana_url_returns_error(self):
        with patch("services.grafana.GRAFANA_URL", ""):
            from services.grafana import fetch_grafana_metric
            result = fetch_grafana_metric("CPU", "some_query")
            assert "Error" in result or "not configured" in result

    def test_connection_error_returns_message(self):
        with patch("services.grafana.requests.get", side_effect=ConnectionError("timeout")), \
             patch("services.grafana.GRAFANA_URL", "http://localhost:3000"):
            from services.grafana import fetch_grafana_metric
            result = fetch_grafana_metric("CPU", "some_query")
            assert "Connection Failed" in result


class TestCaptureDashboard:
    def test_goto_called_with_timeout(self):
        cm, page = _make_playwright_stack()
        with patch("services.grafana.sync_playwright", return_value=cm):
            from services.grafana import capture_dashboard
            capture_dashboard("http://example.com/dashboard", "out.png")
            page.goto.assert_called_once_with(
                "http://example.com/dashboard",
                wait_until="networkidle",
                timeout=30000,
            )

    def test_no_sleep_called(self):
        cm, _ = _make_playwright_stack()
        with patch("services.grafana.sync_playwright", return_value=cm), \
             patch("time.sleep") as mock_sleep:
            from services.grafana import capture_dashboard
            capture_dashboard("http://example.com/dashboard", "out.png")
            mock_sleep.assert_not_called()

    def test_screenshot_saved_to_output_path(self):
        cm, page = _make_playwright_stack()
        with patch("services.grafana.sync_playwright", return_value=cm):
            from services.grafana import capture_dashboard
            result = capture_dashboard("http://example.com/dashboard", "snapshot.png")
            page.screenshot.assert_called_once_with(path="snapshot.png")
            assert result == "snapshot.png"

    def test_returns_none_on_playwright_error(self):
        cm = MagicMock()
        cm.__enter__ = MagicMock(side_effect=Exception("browser crash"))
        cm.__exit__ = MagicMock(return_value=False)
        with patch("services.grafana.sync_playwright", return_value=cm):
            from services.grafana import capture_dashboard
            result = capture_dashboard("http://example.com/dashboard", "out.png")
            assert result is None
