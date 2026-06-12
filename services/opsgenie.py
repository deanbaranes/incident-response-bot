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
async def send_opsgenie_alert(
    title: str, message: str, alert_name: str, priority: str = "P3"
) -> bool:
    """Send alert to OpsGenie via API."""
    if not settings.OPSGENIE_API_KEY:
        raise RuntimeError("settings.OPSGENIE_API_KEY is not configured")

    base_url = "https://api.opsgenie.com"
    if settings.OPSGENIE_REGION.lower() == "eu":
        base_url = "https://api.eu.opsgenie.com"

    url = f"{base_url}/v2/alerts"

    headers = {
        "Authorization": f"GenieKey {settings.OPSGENIE_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "message": title,
        "description": message,
        "priority": priority,
        "source": "Incident Response Bot",
        "details": {"alert_name": alert_name},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()

    logger.info(f"Real OpsGenie alert sent: {title}")
    return True
