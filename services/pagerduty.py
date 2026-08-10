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
async def create_pagerduty_incident(
    title: str, message: str, alert_name: str, severity: str = "critical"
) -> bool:
    """Trigger an incident in PagerDuty via Events API."""
    if not settings.PAGERDUTY_ROUTING_KEY:
        raise RuntimeError("settings.PAGERDUTY_ROUTING_KEY is not configured")

    url = "https://events.pagerduty.com/v2/enqueue"

    payload = {
        "routing_key": settings.PAGERDUTY_ROUTING_KEY,
        "event_action": "trigger",
        "payload": {
            "summary": title,
            "severity": severity,
            "source": "Incident Response Bot",
            "custom_details": {"message": message, "alert_name": alert_name},
        },
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=10.0)
        response.raise_for_status()

    logger.info(f"Real PagerDuty alert sent: {title}")
    return True
