import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock


def _run_send(subject="Test Subject", content="Test body", attachment_path=None,
              recipients=None, sender="bot@example.com", password="test_pass"):
    """Helper: patch module-level config vars and run send_email_report."""
    mock_server = MagicMock()
    with patch("services.email.EMAIL_SENDER", sender), \
         patch("services.email.EMAIL_PASSWORD", password), \
         patch("services.email.EMAIL_HOST", "smtp.example.com"), \
         patch("services.email.EMAIL_PORT", 587), \
         patch("services.email.EMAIL_RECIPIENTS", recipients or []), \
         patch("services.email.smtplib.SMTP", return_value=mock_server):
        from services.email import send_email_report
        send_email_report(subject, content, attachment_path=attachment_path)
    return mock_server


class TestSendEmailReport:
    def test_sendmail_called(self):
        server = _run_send()
        server.sendmail.assert_called_once()

    def test_uses_email_recipients_when_set(self):
        server = _run_send(recipients=["alice@x.com", "bob@x.com"])
        _, recipients_arg, _ = server.sendmail.call_args[0]
        assert "alice@x.com" in recipients_arg
        assert "bob@x.com" in recipients_arg

    def test_falls_back_to_sender_when_no_recipients(self):
        server = _run_send(sender="bot@example.com", recipients=[])
        _, recipients_arg, _ = server.sendmail.call_args[0]
        assert "bot@example.com" in recipients_arg

    def test_subject_in_message(self):
        server = _run_send(subject="INCIDENT: HighCPU")
        _, _, raw_msg = server.sendmail.call_args[0]
        assert "INCIDENT: HighCPU" in raw_msg

    def test_starttls_called(self):
        server = _run_send()
        server.starttls.assert_called_once()

    def test_login_called_with_credentials(self):
        server = _run_send(sender="bot@example.com", password="s3cr3t")
        server.login.assert_called_once_with("bot@example.com", "s3cr3t")

    def test_quit_called_after_send(self):
        server = _run_send()
        server.quit.assert_called_once()

    def test_attachment_included_when_file_exists(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"fake png")
            tmp = f.name
        try:
            server = _run_send(attachment_path=tmp)
            _, _, raw_msg = server.sendmail.call_args[0]
            assert len(raw_msg) > 100
        finally:
            os.unlink(tmp)

    def test_no_attachment_when_path_missing(self):
        server = _run_send(attachment_path="/nonexistent/file.png")
        server.sendmail.assert_called_once()

    def test_smtp_error_does_not_raise(self):
        mock_server = MagicMock()
        mock_server.starttls.side_effect = Exception("SMTP connection refused")
        with patch("services.email.smtplib.SMTP", return_value=mock_server), \
             patch("services.email.EMAIL_SENDER", "bot@example.com"), \
             patch("services.email.EMAIL_PASSWORD", "pass"), \
             patch("services.email.EMAIL_HOST", "smtp.example.com"), \
             patch("services.email.EMAIL_PORT", 587), \
             patch("services.email.EMAIL_RECIPIENTS", []):
            from services.email import send_email_report
            send_email_report("Test", "Body")  # must not raise
