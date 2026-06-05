import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging
from config import (
    EMAIL_SENDER,
    EMAIL_PASSWORD,
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_RECIPIENTS,
)
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


# Helper function to build and send the final report email
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def send_email_report(subject, content, attachment_path=None):
    """Send incident report via SMTP."""
    recipients = EMAIL_RECIPIENTS if EMAIL_RECIPIENTS else [EMAIL_SENDER]
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(content, "plain"))

    # Check if we have a dashboard screenshot to attach
    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())

        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={os.path.basename(attachment_path)}",
        )
        msg.attach(part)

    server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
    server.starttls()
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
    server.sendmail(EMAIL_SENDER, recipients, msg.as_string())
    server.quit()
    logger.info("Email sent successfully.")
