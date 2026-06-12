from unittest.mock import patch, MagicMock
from services.slack import send_slack_alert


@patch("services.slack.requests.post")
@patch(
    "core.settings.settings.SLACK_WEBHOOK_URL",
    "https://hooks.slack.com/services/T000/B000/XXX",
)
def test_send_slack_alert_payload(mock_post):
    """Test Slack payload generation without screenshot."""
    mock_response = MagicMock()
    mock_post.return_value = mock_response

    result = send_slack_alert("CPU is high", "Critical Alert")
    assert result is True

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args

    # Assert URL
    assert args[0] == "https://hooks.slack.com/services/T000/B000/XXX"

    # Assert JSON payload
    payload = kwargs["json"]
    assert "text" in payload
    assert "*Critical Alert*" in payload["text"]
    assert "CPU is high" in payload["text"]
    assert "📎 *Visual Evidence*" not in payload["text"]


@patch("services.slack.requests.post")
@patch(
    "core.settings.settings.SLACK_WEBHOOK_URL",
    "https://hooks.slack.com/services/T000/B000/XXX",
)
def test_send_slack_alert_with_screenshot(mock_post):
    """Test Slack payload generation WITH screenshot."""
    mock_response = MagicMock()
    mock_post.return_value = mock_response

    result = send_slack_alert("Memory is high", screenshot_path="/tmp/shot.png")
    assert result is True

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args

    payload = kwargs["json"]
    assert "📎 *Visual Evidence*" in payload["text"]
    assert "`/tmp/shot.png`" in payload["text"]
