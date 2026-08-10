from unittest.mock import AsyncMock, patch

import pytest

from services.jira import create_jira_ticket


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post", new_callable=AsyncMock)
@patch("core.settings.settings.JIRA_BASE_URL", "https://test.atlassian.net")
@patch("core.settings.settings.JIRA_USER", "test@example.com")
@patch("core.settings.settings.JIRA_API_TOKEN", "token123")
@patch("core.settings.settings.JIRA_PROJECT_KEY", "TEST")
async def test_create_jira_ticket_payload(mock_post):
    """Test Jira payload generation and authentication."""
    from unittest.mock import MagicMock

    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "TEST-1"}
    mock_post.return_value = mock_response

    result = await create_jira_ticket("High CPU", "CPU is at 99%")
    assert result is True

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args

    # Assert URL
    assert args[0] == "https://test.atlassian.net/rest/api/3/issue"

    # Assert Auth
    assert kwargs["auth"] == ("test@example.com", "token123")

    # Assert Document Format Payload
    payload = kwargs["json"]
    assert payload["fields"]["project"]["key"] == "TEST"
    assert payload["fields"]["summary"] == "High CPU"
    assert payload["fields"]["issuetype"]["name"] == "Task"

    # Check Atlassian Document Format nested structure
    description_content = payload["fields"]["description"]["content"][0]["content"][0][
        "text"
    ]
    assert description_content == "CPU is at 99%"
