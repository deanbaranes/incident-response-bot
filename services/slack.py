import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.settings import settings

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.RequestError),
    reraise=True,
)
async def send_slack_alert(
    message: str, title: str = "Incident Alert", screenshot_path: str | None = None
) -> bool:
    """Send an alert to Slack via Incoming Webhook."""

    if screenshot_path:
        message += f"\n\n📎 *Visual Evidence*: A screenshot was captured and saved locally at: `{screenshot_path}`"

    if not settings.SLACK_WEBHOOK_URL:
        # Fallback Mock if webhook is not configured
        logger.info(f"MOCK SLACK ALERT: Title: {title} | Message: {message[:100]}...")
        return True

    payload = {"text": f"*{title}*\n{message}"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.SLACK_WEBHOOK_URL, json=payload, timeout=10.0
        )
        response.raise_for_status()

    logger.info(f"Successfully sent Slack alert: {title}")
    return True
