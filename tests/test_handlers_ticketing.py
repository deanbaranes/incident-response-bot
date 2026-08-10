from unittest.mock import AsyncMock, patch

import pytest

from core.actions.handlers.ticketing import (
    CreateJiraTicketHandler,
    CreatePagerDutyIncidentHandler,
    SendGrafanaOnCallAlertHandler,
    SendOpsGenieAlertHandler,
)
from core.context import IncidentContext


@pytest.fixture
def dummy_context():
    ctx = IncidentContext(alert_name="TestAlert")
    ctx.summary = "Test Summary"
    ctx.enriched_data = ["log1", "log2"]
    ctx.ai_output = "Fix it"
    return ctx


@pytest.mark.asyncio
async def test_create_jira_ticket_handler(dummy_context):
    handler = CreateJiraTicketHandler()
    action = {"type": "create_jira_ticket"}

    with patch(
        "core.actions.handlers.ticketing.create_jira_ticket", new_callable=AsyncMock
    ) as mock_create:
        await handler.execute(action, dummy_context, {})
        mock_create.assert_called_once()
        args, kwargs = mock_create.call_args
        assert "TestAlert" in kwargs["summary"]
        assert "Test Summary" in kwargs["description"]
        assert "Ticketing: Jira ticket created." in dummy_context.execution_steps


@pytest.mark.asyncio
async def test_create_pagerduty_incident_handler(dummy_context):
    handler = CreatePagerDutyIncidentHandler()
    action = {
        "type": "create_pagerduty_incident",
        "severity": "info",
        "title": "PD Title",
    }

    with patch(
        "core.actions.handlers.ticketing.create_pagerduty_incident",
        new_callable=AsyncMock,
    ) as mock_create:
        await handler.execute(action, dummy_context, {})
        mock_create.assert_called_once_with(
            title="PD Title",
            message="Test Summary",
            alert_name="TestAlert",
            severity="info",
        )
        assert "Notification: PagerDuty triggered." in dummy_context.execution_steps


@pytest.mark.asyncio
async def test_send_opsgenie_alert_handler(dummy_context):
    handler = SendOpsGenieAlertHandler()
    action = {"type": "send_opsgenie_alert", "priority": "P1", "title": "Ops Title"}

    with patch(
        "core.actions.handlers.ticketing.send_opsgenie_alert", new_callable=AsyncMock
    ) as mock_send:
        await handler.execute(action, dummy_context, {})
        mock_send.assert_called_once_with(
            title="Ops Title",
            message="Test Summary",
            alert_name="TestAlert",
            priority="P1",
        )
        assert "Notification: OpsGenie triggered." in dummy_context.execution_steps


@pytest.mark.asyncio
async def test_send_grafana_oncall_alert_handler(dummy_context):
    handler = SendGrafanaOnCallAlertHandler()
    action = {"type": "send_grafana_oncall_alert", "title": "Grafana Title"}

    with patch(
        "core.actions.handlers.ticketing.send_grafana_oncall_alert",
        new_callable=AsyncMock,
    ) as mock_send:
        await handler.execute(action, dummy_context, {})
        mock_send.assert_called_once_with(
            title="Grafana Title", message="Test Summary", alert_name="TestAlert"
        )
        assert (
            "Notification: Grafana OnCall triggered." in dummy_context.execution_steps
        )
