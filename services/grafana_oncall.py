import logging
from config import GRAFANA_ONCALL_WEBHOOK_URL

logger = logging.getLogger(__name__)

def send_grafana_oncall_alert(title: str, message: str, alert_name: str) -> bool:
    """Mock implementation for Grafana OnCall."""
    if not GRAFANA_ONCALL_WEBHOOK_URL:
        logger.info(f"MOCK GRAFANA ONCALL ALERT: {title} - {message[:50]}...")
        return True
    
    # Real integration would use requests.post to the webhook URL
    logger.info(f"Real Grafana OnCall alert sent: {title}")
    return True
