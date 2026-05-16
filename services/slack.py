import logging
import requests
from config import SLACK_WEBHOOK_URL

logger = logging.getLogger(__name__)

def send_slack_alert(message: str, title: str = "Incident Alert") -> bool:
    """Send an alert to Slack via Incoming Webhook."""
    if not SLACK_WEBHOOK_URL:
        # Fallback Mock if webhook is not configured
        logger.info(f"MOCK SLACK ALERT: Title: {title} | Message: {message[:100]}...")
        return True
        
    payload = {
        "text": f"*{title}*\n{message}"
    }
    
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Successfully sent Slack alert: {title}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Slack alert: {e}")
        return False
