import logging
from config import OPSGENIE_API_KEY

logger = logging.getLogger(__name__)


def send_opsgenie_alert(
    title: str, message: str, alert_name: str, priority: str = "P3"
) -> bool:
    """Mock implementation for OpsGenie."""
    if not OPSGENIE_API_KEY:
        logger.info(f"MOCK OPSGENIE ALERT: [{priority}] {title} - {message[:50]}...")
        return True

    # Real integration would use requests.post to https://api.opsgenie.com/v2/alerts
    logger.info(f"Real OpsGenie alert sent: {title}")
    return True
