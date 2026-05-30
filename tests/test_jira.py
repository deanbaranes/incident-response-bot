from unittest.mock import patch, MagicMock
from services.jira import create_jira_ticket
from requests.auth import HTTPBasicAuth


@patch("services.jira.requests.post")
@patch("services.jira.JIRA_BASE_URL", "https://test.atlassian.net")
@patch("services.jira.JIRA_USER", "test@example.com")
@patch("services.jira.JIRA_API_TOKEN", "token123")
@patch("services.jira.JIRA_PROJECT_KEY", "TEST")
def test_create_jira_ticket_payload(mock_post):
    """Test Jira payload generation and authentication."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"key": "TEST-1"}
    mock_post.return_value = mock_response

    result = create_jira_ticket("High CPU", "CPU is at 99%")
    assert result is True

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args

    # Assert URL
    assert args[0] == "https://test.atlassian.net/rest/api/3/issue"

    # Assert Auth
    assert isinstance(kwargs["auth"], HTTPBasicAuth)
    assert kwargs["auth"].username == "test@example.com"
    assert kwargs["auth"].password == "token123"

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
