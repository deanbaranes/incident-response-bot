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
EMAIL_RECIPIENTS = [
    r.strip() for r in os.getenv("EMAIL_RECIPIENTS", "").split(",") if r.strip()
]

# Optional — when set, webhook requests must carry a matching HMAC-SHA256 signature.
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# --- Validation ---
_REQUIRED = [
    "GEMINI_API_KEY",
    "EMAIL_SENDER",
    "EMAIL_PASSWORD",
    "GRAFANA_TOKEN",
    "GRAFANA_URL",
]

_missing = [name for name in _REQUIRED if not os.getenv(name)]
if _missing:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(_missing)}. "
        "Copy .env.example to .env and fill in the values."
    )
