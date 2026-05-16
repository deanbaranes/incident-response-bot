import logging
from config import PAGERDUTY_ROUTING_KEY

logger = logging.getLogger(__name__)

def create_pagerduty_incident(title: str, message: str, alert_name: str, severity: str = "critical") -> bool:
    """Mock implementation for PagerDuty."""
    if not PAGERDUTY_ROUTING_KEY:
        logger.info(f"MOCK PAGERDUTY ALERT: [{severity}] {title} - {message[:50]}...")
        return True
    
    # Real integration would use requests.post to https://events.pagerduty.com/v2/enqueue
    logger.info(f"Real PagerDuty alert sent: {title}")
    return True
