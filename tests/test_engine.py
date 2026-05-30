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

    # Deep Assertion: Check AI analysis was called with correct context
    mock_get_ai.assert_called_once()
    ai_args, ai_kwargs = mock_get_ai.call_args
    assert "HighCPUUsage" in ai_args[0]
    assert "85%" in ai_args[1]  # Enriched data should contain the fetched metric

    # Deep Assertion: Check email was sent with correct structured report
    mock_send_email.assert_called_once()
    email_args, email_kwargs = mock_send_email.call_args
    assert "Incident Report: HighCPUUsage" in email_args[0]
    email_body = email_args[1]
    assert "CPU over 90%" in email_body  # Summary
    assert "85%" in email_body  # Live Context
    assert "AI Insight" in email_body  # RCA


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
    mock_get_ai.assert_called_once_with("UnknownAlert", "Something went wrong")
    # Email should still be sent with fallback subject
    mock_send_email.assert_called_once()
    args, kwargs = mock_send_email.call_args
    assert "No Playbook Found" in args[0]


@pytest.mark.asyncio
@patch("core.engine.load_playbook")
@patch("core.engine.send_slack_alert")
@patch("core.engine.create_jira_ticket")
@patch("core.engine.get_ai_analysis")
async def test_process_incident_with_new_integrations(
    mock_get_ai, mock_create_jira, mock_send_slack, mock_load_playbook
):
    """Test process_incident routing for Slack and Jira actions."""
    mock_load_playbook.return_value = {
        "name": "Integration Playbook",
        "actions": [
            {"type": "send_slack_notification"},
            {"type": "create_jira_ticket"},
        ],
    }
    mock_get_ai.return_value = "AI Insight"

    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "TestAlert"},
                "annotations": {"summary": "Alert summary"},
            }
        ]
    }

    await process_incident(payload)

    # Check playbook loaded
    mock_load_playbook.assert_called_once_with("TestAlert")
    # Deep Assertion: Check Slack payload
    mock_send_slack.assert_called_once()
    slack_args, slack_kwargs = mock_send_slack.call_args
    assert "Alert summary" in slack_args[0]
    assert slack_kwargs["title"] == "Incident Alert: TestAlert"

    # Deep Assertion: Check Jira payload
    mock_create_jira.assert_called_once()
    jira_args, jira_kwargs = mock_create_jira.call_args
    assert jira_kwargs["summary"] == "[TestAlert] Incident Alert"
    assert "Alert summary" in jira_kwargs["description"]
