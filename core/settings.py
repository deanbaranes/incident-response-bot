import logging
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Required core integrations
    GEMINI_API_KEY: str
    WEBHOOK_SECRET: str

    # Email Settings
    EMAIL_SENDER: str
    EMAIL_PASSWORD: str
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_RECIPIENTS: str = ""

    @property
    def email_recipients_list(self) -> List[str]:
        return [r.strip() for r in self.EMAIL_RECIPIENTS.split(",") if r.strip()]

    # Grafana Settings
    GRAFANA_URL: str
    GRAFANA_TOKEN: str
    GRAFANA_USERNAME: Optional[str] = None
    GRAFANA_DASHBOARD_URL: Optional[str] = None
    GRAFANA_PROMETHEUS_DATASOURCE_ID: str = "8"

    # Optional Integrations
    SLACK_WEBHOOK_URL: Optional[str] = None

    # Jira
    JIRA_BASE_URL: Optional[str] = None
    JIRA_USER: Optional[str] = None
    JIRA_API_TOKEN: Optional[str] = None
    JIRA_PROJECT_KEY: Optional[str] = None

    # Other integrations
    GRAFANA_ONCALL_WEBHOOK_URL: Optional[str] = None
    OPSGENIE_API_KEY: Optional[str] = None
    OPSGENIE_REGION: str = "us"
    PAGERDUTY_ROUTING_KEY: Optional[str] = None

    # Kafka Settings
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:9092"
    KAFKA_INCIDENT_TOPIC: str = "incident.webhooks"
    KAFKA_CONSUMER_GROUP: str = "incident-responder"
    KAFKA_DLQ_TOPIC: str = "incident.webhooks.dlq"
    USE_KAFKA_QUEUE: bool = False


try:
    settings = Settings()  # type: ignore
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise RuntimeError(f"Missing or invalid configuration: {e}")
