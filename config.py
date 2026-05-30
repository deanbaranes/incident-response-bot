import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Initialize Environment Variables
load_dotenv()

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_USERNAME = os.getenv("GRAFANA_USERNAME")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")
GRAFANA_DASHBOARD_URL = os.getenv("GRAFANA_DASHBOARD_URL")
GRAFANA_PROMETHEUS_DATASOURCE_ID = os.getenv("GRAFANA_PROMETHEUS_DATASOURCE_ID", "8")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# Jira
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")

# Other mock integrations
GRAFANA_ONCALL_WEBHOOK_URL = os.getenv("GRAFANA_ONCALL_WEBHOOK_URL")
OPSGENIE_API_KEY = os.getenv("OPSGENIE_API_KEY")
PAGERDUTY_ROUTING_KEY = os.getenv("PAGERDUTY_ROUTING_KEY")
EMAIL_RECIPIENTS = [
    r.strip() for r in os.getenv("EMAIL_RECIPIENTS", "").split(",") if r.strip()
]

# Optional — when set, webhook requests must carry a matching HMAC-SHA256 signature.
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# Kafka Settings
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_INCIDENT_TOPIC = os.getenv("KAFKA_INCIDENT_TOPIC", "incident.webhooks")
KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "incident-responder")
KAFKA_DLQ_TOPIC = os.getenv("KAFKA_DLQ_TOPIC", "incident.webhooks.dlq")
USE_KAFKA_QUEUE = os.getenv("USE_KAFKA_QUEUE", "false").lower() == "true"

# --- Validation ---
_REQUIRED = [
    "GEMINI_API_KEY",
    "EMAIL_SENDER",
    "EMAIL_PASSWORD",
    "GRAFANA_TOKEN",
    "GRAFANA_URL",
    "WEBHOOK_SECRET",
]

_missing = [name for name in _REQUIRED if not os.getenv(name)]
if _missing:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(_missing)}. "
        "Copy .env.example to .env and fill in the values."
    )
