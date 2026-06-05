from unittest.mock import patch, MagicMock
import requests
from services.grafana import (
    fetch_grafana_metric,
    capture_dashboard,
    execute_grafana_query,
)


@patch("services.grafana.requests.get")
def test_fetch_grafana_metric_empty(mock_get):
    """Test when Prometheus returns an empty array."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"data": {"result": []}}
    mock_get.return_value = mock_response

    result = fetch_grafana_metric("CPU", "avg(cpu)")
    assert result == "No active data points found."


@patch("services.grafana.requests.get")
def test_fetch_grafana_metric_timeout(mock_get):
    """Test when requests raises a Timeout exception."""
    mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

    result = fetch_grafana_metric("CPU", "avg(cpu)")
    assert "Connection Failed" in result
    assert "Connection timed out" in result


def test_capture_dashboard_ssrf_malicious_domain():
    """Test SSRF protection blocks completely external domain."""
    result = capture_dashboard("https://malicious-site.com/dashboard", "out.png")
    assert result is None


def test_capture_dashboard_ssrf_naive_bypass():
    """Test SSRF protection blocks naive subdomain bypass."""
    # This tries to trick naive string checking like `if "dinbaranes.grafana.net" in url`
    result = capture_dashboard(
        "https://dinbaranes.grafana.net.attacker.com/dash", "out.png"
    )
    assert result is None


def test_fetch_grafana_metric_blocked_range():
    """Test PromQL regex validation blocks years, weeks, and days."""
    result_year = fetch_grafana_metric("CPU", "avg_over_time(cpu[1y])")
    assert "Blocked: Time range too large" in result_year

    result_week = fetch_grafana_metric("CPU", "rate(errors[52w])")
    assert "Blocked: Time range too large" in result_week

    result_day = fetch_grafana_metric("CPU", "sum(cpu[ 10 d ])")
    assert "Blocked: Time range too large" in result_day

    # Hours should be allowed
    with patch("services.grafana.requests.get") as mock_get:
        mock_response = MagicMock()
        mock_response.json.return_value = {"data": {"result": []}}
        mock_get.return_value = mock_response
        result_hour = fetch_grafana_metric("CPU", "avg_over_time(cpu[5h])")
        assert result_hour == "No active data points found."


@patch("services.grafana.requests.post")
def test_execute_grafana_query_success(mock_post):
    """Test successful grafana query parses data cleanly."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": {
            "A": {
                "frames": [
                    {
                        "schema": {"fields": [{"name": "Time"}, {"name": "Value"}]},
                        "data": {"values": [[1600000000, 1600000060], [10.5, 20.0]]},
                    }
                ]
            }
        }
    }
    mock_post.return_value = mock_response

    result = execute_grafana_query("my-uid", "avg(metric)")
    assert "Columns: Time, Value" in result
    assert "1600000000 | 10.5" in result
    assert "1600000060 | 20.0" in result


@patch("services.grafana.requests.post")
def test_execute_grafana_query_empty(mock_post):
    """Test when grafana query returns empty frames."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"results": {"A": {"frames": []}}}
    mock_post.return_value = mock_response

    result = execute_grafana_query("my-uid", "avg(metric)")
    assert result == "Grafana Query returned successfully with NO data/rows found."


@patch("services.grafana.requests.post")
def test_execute_grafana_query_timeout(mock_post):
    """Test when requests raises a Timeout exception for grafana query."""
    mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

    result = execute_grafana_query("my-uid", "avg(metric)")
    assert "Connection Failed" in result
    assert "Connection timed out" in result
