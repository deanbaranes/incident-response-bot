import base64
import pytest
import yaml
from unittest.mock import patch, MagicMock


def _make_github_response(playbook_dict, status_code=200):
    content = base64.b64encode(yaml.dump(playbook_dict).encode()).decode()
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = {"content": content}
    mock_resp.raise_for_status.side_effect = None if status_code == 200 else Exception("404")
    return mock_resp


class TestLoadPlaybook:
    def test_filename_spaces_to_underscores_lowercase(self, sample_playbook):
        with patch("services.github.requests.get") as mock_get:
            mock_get.return_value = _make_github_response(sample_playbook)
            from services.github import load_playbook
            load_playbook("High CPU Usage")
            called_url = mock_get.call_args[0][0]
            assert "high_cpu_usage.yaml" in called_url

    def test_returns_parsed_yaml(self, sample_playbook):
        with patch("services.github.requests.get") as mock_get:
            mock_get.return_value = _make_github_response(sample_playbook)
            from services.github import load_playbook
            result = load_playbook("HighCPUUsage")
            assert result["name"] == sample_playbook["name"]
            assert len(result["actions"]) == len(sample_playbook["actions"])

    def test_uses_bearer_token_header(self, sample_playbook):
        with patch("services.github.requests.get") as mock_get:
            mock_get.return_value = _make_github_response(sample_playbook)
            from services.github import load_playbook
            load_playbook("HighCPUUsage")
            headers = mock_get.call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("token ")

    def test_returns_none_on_http_error(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404 Not Found")
        with patch("services.github.requests.get", return_value=mock_resp):
            from services.github import load_playbook
            result = load_playbook("NonExistentAlert")
            assert result is None

    def test_returns_none_on_connection_error(self):
        with patch("services.github.requests.get", side_effect=ConnectionError("timeout")):
            from services.github import load_playbook
            result = load_playbook("HighCPUUsage")
            assert result is None

    def test_repo_and_alert_name_in_url(self, sample_playbook):
        with patch("services.github.requests.get") as mock_get, \
             patch("services.github.GITHUB_REPO", "myorg/myrepo"):
            mock_get.return_value = _make_github_response(sample_playbook)
            from services.github import load_playbook
            load_playbook("TestAlert")
            called_url = mock_get.call_args[0][0]
            assert "myorg/myrepo" in called_url
            assert "testalert.yaml" in called_url
