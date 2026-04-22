import requests
import base64
import yaml
import logging
from config import GITHUB_REPO, GITHUB_TOKEN

logger = logging.getLogger(__name__)


# Fetches the specific playbook YAML file for the given alert from our repository
# We use this to know exactly what actions to run for each incident
def load_playbook(alert_name):
    """Download playbook from GitHub repository."""
    file_name = alert_name.replace(" ", "_").lower()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/playbooks/{file_name}.yaml"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"GitHub Request URL: {url}")
        content = base64.b64decode(response.json()["content"]).decode("utf-8")
        return yaml.safe_load(content)
    except Exception as e:
        logger.error(f"GitHub Error: {e}")
        return None
