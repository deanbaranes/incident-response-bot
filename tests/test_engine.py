import pytest
from unittest.mock import patch
from core.engine import process_incident


@pytest.mark.asyncio
@patch("core.engine.load_playbook")
@patch("core.engine.capture_dashboard")
@patch("core.engine.fetch_grafana_metric")
@patch("core.engine.get_ai_analysis")
@patch("core.engine.send_email_report")
async def test_process_incident_with_playbook(
    mock_send_email, mock_get_ai, mock_fetch_metric, mock_capture, mock_load_playbook
):
    """Test process_incident when a playbook is found."""
    mock_load_playbook.return_value = {
        "name": "Test Playbook",
        "actions": [
            {"type": "fetch_metrics", "target": "CPU"},
            {"type": "ai_analysis"},
            {"type": "send_notification"},
        ],
    }
    mock_fetch_metric.return_value = "85%"
    mock_get_ai.return_value = "AI Insight"

    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "HighCPUUsage"},
                "annotations": {"summary": "CPU over 90%"},
            }
        ]
    }

    await process_incident(payload)

    # Check playbook was loaded
    mock_load_playbook.assert_called_once_with("HighCPUUsage")
    # Check metric was fetched
    mock_fetch_metric.assert_called_once()
    # Check AI analysis was called
    mock_get_ai.assert_called_once()
    # Check email was sent
    mock_send_email.assert_called_once()


@pytest.mark.asyncio
@patch("core.engine.load_playbook")
@patch("core.engine.get_ai_analysis")
@patch("core.engine.send_email_report")
async def test_process_incident_fallback(
    mock_send_email, mock_get_ai, mock_load_playbook
):
    """Test process_incident fallback when playbook is NOT found."""
    mock_load_playbook.return_value = None
    mock_get_ai.return_value = "Basic AI Insight"

    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "UnknownAlert"},
                "annotations": {"summary": "Something went wrong"},
            }
        ]
    }

    await process_incident(payload)

    mock_load_playbook.assert_called_once_with("UnknownAlert")
    # AI should still be called
    mock_get_ai.assert_called_once_with(
        "UnknownAlert", "Something went wrong", screenshot_path=None
    )
    # Email should still be sent with fallback subject
    mock_send_email.assert_called_once()
    args, kwargs = mock_send_email.call_args
    assert "No Playbook Found" in args[0]
