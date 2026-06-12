import logging
import httpx
from core.settings import settings
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.RequestError),
    reraise=True,
)
async def send_grafana_oncall_alert(title: str, message: str, alert_name: str) -> bool:
    """Send alert to Grafana OnCall via webhook."""
    if not settings.GRAFANA_ONCALL_WEBHOOK_URL:
        raise RuntimeError("settings.GRAFANA_ONCALL_WEBHOOK_URL is not configured")

    payload = {
        "title": title,
        "message": message,
        "alert_name": alert_name,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.GRAFANA_ONCALL_WEBHOOK_URL, json=payload, timeout=10.0
        )
        response.raise_for_status()

    logger.info(f"Real Grafana OnCall alert sent: {title}")
    return True
