from unittest.mock import patch, MagicMock
from services.email import send_email_report


@patch("services.email.smtplib.SMTP")
@patch(
    "core.settings.settings.EMAIL_RECIPIENTS", "test1@example.com, test2@example.com"
)
@patch("core.settings.settings.EMAIL_SENDER", "sender@example.com")
@patch("core.settings.settings.EMAIL_PASSWORD", "password")
@patch("core.settings.settings.EMAIL_HOST", "smtp.test.com")
@patch("core.settings.settings.EMAIL_PORT", 587)
def test_send_email_report_multiple_recipients(mock_smtp):
    mock_server = MagicMock()
    mock_smtp.return_value = mock_server

    send_email_report("Test Subject", "Test Content")

    mock_smtp.assert_called_once_with("smtp.test.com", 587)
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("sender@example.com", "password")

    # Check that sendmail was called with the correct list of recipients
    args, kwargs = mock_server.sendmail.call_args
    assert args[0] == "sender@example.com"
    assert args[1] == ["test1@example.com", "test2@example.com"]
    assert "To: test1@example.com, test2@example.com" in args[2]


@patch("services.email.smtplib.SMTP")
@patch("core.settings.settings.EMAIL_RECIPIENTS", "")
@patch("core.settings.settings.EMAIL_SENDER", "sender@example.com")
def test_send_email_report_fallback_to_sender(mock_smtp):
    mock_server = MagicMock()
    mock_smtp.return_value = mock_server

    send_email_report("Test Subject", "Test Content")

    args, kwargs = mock_server.sendmail.call_args
    assert args[1] == ["sender@example.com"]
    assert "To: sender@example.com" in args[2]


@patch("services.email.smtplib.SMTP")
@patch("services.email.os.path.exists")
@patch("builtins.open", new_callable=MagicMock)
def test_send_email_report_with_attachment(mock_open, mock_exists, mock_smtp):
    mock_exists.return_value = True
    mock_file = MagicMock()
    mock_file.read.return_value = b"fake image content"
    mock_open.return_value.__enter__.return_value = mock_file

    mock_server = MagicMock()
    mock_smtp.return_value = mock_server

    send_email_report("Test Subject", "Test Content", "test.png")

    args, kwargs = mock_server.sendmail.call_args
    assert "filename=test.png" in args[2]
    mock_open.assert_called_once_with("test.png", "rb")
