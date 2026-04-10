import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Initialize Environment Variables
load_dotenv()

# --- Configuration ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_USERNAME = os.getenv("GRAFANA_USERNAME")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")
GRAFANA_DASHBOARD_URL = os.getenv("GRAFANA_DASHBOARD_URL")

# Check required environment variables to prevent crashes
missing_envs = [name for name in ["GITHUB_TOKEN", "GITHUB_REPO", "GEMINI_API_KEY", "EMAIL_SENDER", "EMAIL_PASSWORD", "GRAFANA_TOKEN", "GRAFANA_URL"] if not os.getenv(name)]
if missing_envs:
    logger.warning(f"The following essential environment variables are missing: {', '.join(missing_envs)}")
