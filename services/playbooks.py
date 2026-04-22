import os
import yaml
import logging

logger = logging.getLogger(__name__)

PLAYBOOKS_DIR = os.getenv(
    "PLAYBOOKS_DIR", os.path.join(os.path.dirname(__file__), "..", "playbooks")
)


def load_playbook(alert_name: str) -> dict | None:
    """Load a playbook YAML from the local playbooks directory."""
    file_name = alert_name.replace(" ", "_").lower() + ".yaml"
    path = os.path.join(PLAYBOOKS_DIR, file_name)

    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"No playbook found for '{alert_name}' at {path}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse playbook {path}: {e}")
        return None
