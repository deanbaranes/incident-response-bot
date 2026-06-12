import pytest
from unittest.mock import patch, AsyncMock
from core.context import IncidentContext
from core.actions.handlers.notifications import (
    SendEmailNotificationHandler,
    SendSlackNotificationHandler,
)


@pytest.fixture
def dummy_context():
    ctx = IncidentContext(alert_name="TestAlert")
    ctx.summary = "Test Summary"
    ctx.enriched_data = ["log1", "log2"]
    ctx.ai_output = "Fix it"
    ctx.screenshots = ["test.png"]
    return ctx


@pytest.mark.asyncio
async def test_send_notification_handler(dummy_context):
    handler = SendEmailNotificationHandler()
    action = {"type": "send_notification"}

    with patch("core.actions.handlers.notifications.send_email_report"):
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            await handler.execute(action, dummy_context, {})

            mock_thread.assert_called_once()
            args, kwargs = mock_thread.call_args
            assert "TestAlert" in kwargs.get(
                "subject", args[1] if len(args) > 1 else ""
            )
            assert "Test Summary" in kwargs.get(
                "content", args[2] if len(args) > 2 else ""
            )
            assert "test.png" == kwargs.get(
                "attachment_path", args[3] if len(args) > 3 else ""
            )
            assert any(
                "RCA report dispatched" in step
                for step in dummy_context.execution_steps
            )


@pytest.mark.asyncio
async def test_send_slack_notification_handler(dummy_context):
    handler = SendSlackNotificationHandler()
    action = {"type": "send_slack_notification"}

    with patch("core.actions.handlers.notifications.send_slack_alert"):
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            await handler.execute(action, dummy_context, {})

            mock_thread.assert_called_once()
            args, kwargs = mock_thread.call_args
            assert "TestAlert" in kwargs.get("title", args[1] if len(args) > 1 else "")
            assert (
                "Test Summary" in args[1]
            )  # slack_message is args[1] because send_slack_alert is args[0]
            assert any(
                "Slack alert dispatched" in step
                for step in dummy_context.execution_steps
            )
