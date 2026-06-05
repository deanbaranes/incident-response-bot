import logging
import requests
from config import SLACK_WEBHOOK_URL
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def send_slack_alert(
    message: str, title: str = "Incident Alert", screenshot_path: str | None = None
) -> bool:
    """Send an alert to Slack via Incoming Webhook."""

    if screenshot_path:
        message += f"\n\n📎 *Visual Evidence*: A screenshot was captured and saved locally at: `{screenshot_path}`"

    if not SLACK_WEBHOOK_URL:
        # Fallback Mock if webhook is not configured
        logger.info(f"MOCK SLACK ALERT: Title: {title} | Message: {message[:100]}...")
        return True

    payload = {"text": f"*{title}*\n{message}"}

    response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    response.raise_for_status()
    logger.info(f"Successfully sent Slack alert: {title}")
    return True
