import os
import importlib
import pytest


def _reload_config(monkeypatch, overrides):
    """Reload config module with a modified environment."""
    import config as cfg_module
    for key, value in overrides.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    return importlib.reload(cfg_module)


def test_email_recipients_parses_comma_list(monkeypatch):
    cfg = _reload_config(monkeypatch, {"EMAIL_RECIPIENTS": "a@x.com, b@x.com , c@x.com"})
    assert cfg.EMAIL_RECIPIENTS == ["a@x.com", "b@x.com", "c@x.com"]


def test_email_recipients_empty_string_gives_empty_list(monkeypatch):
    cfg = _reload_config(monkeypatch, {"EMAIL_RECIPIENTS": ""})
    assert cfg.EMAIL_RECIPIENTS == []


def test_email_port_defaults_to_587(monkeypatch):
    cfg = _reload_config(monkeypatch, {"EMAIL_PORT": None})
    assert cfg.EMAIL_PORT == 587


def test_email_host_defaults_to_gmail(monkeypatch):
    cfg = _reload_config(monkeypatch, {"EMAIL_HOST": None})
    assert cfg.EMAIL_HOST == "smtp.gmail.com"


def test_missing_required_var_raises(monkeypatch):
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        _reload_config(monkeypatch, {"GEMINI_API_KEY": None})


def test_webhook_secret_optional(monkeypatch):
    cfg = _reload_config(monkeypatch, {"WEBHOOK_SECRET": None})
    assert cfg.WEBHOOK_SECRET is None


def test_all_required_vars_present_no_error(monkeypatch):
    # Should not raise when all required vars are set (conftest sets them)
    cfg = _reload_config(monkeypatch, {})
    assert cfg.GITHUB_TOKEN == os.environ["GITHUB_TOKEN"]
