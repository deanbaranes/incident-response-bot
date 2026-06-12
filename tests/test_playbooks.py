from unittest.mock import patch, mock_open
from services.playbooks import load_playbook


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="name: Test Playbook\ninstruction: Fix it\nactions:\n  - type: ai_analysis",
)
@patch("os.path.join")
def test_load_playbook_success(mock_join, mock_file):
    mock_join.return_value = "/fake/dir/high_cpu_usage.yaml"

    result = load_playbook("High CPU Usage")

    assert result is not None
    assert result["name"] == "Test Playbook"
    assert result["instruction"] == "Fix it"
    assert len(result["actions"]) == 1
    assert result["actions"][0]["type"] == "ai_analysis"


@patch("builtins.open")
def test_load_playbook_not_found(mock_file):
    mock_file.side_effect = FileNotFoundError()

    result = load_playbook("Nonexistent Alert")
    assert result is None


@patch("builtins.open", new_callable=mock_open, read_data="name: [invalid yaml")
def test_load_playbook_invalid_yaml(mock_file):
    result = load_playbook("Bad YAML Alert")
    assert result is None
