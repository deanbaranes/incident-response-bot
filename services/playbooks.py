import logging
import os
import re

import yaml

logger = logging.getLogger(__name__)

PLAYBOOKS_DIR = os.getenv(
    "PLAYBOOKS_DIR", os.path.join(os.path.dirname(__file__), "..", "playbooks")
)


def load_playbook(alert_name: str) -> dict | None:
    """Load a playbook YAML from the local playbooks directory."""
    # Prevent path traversal by sanitizing the name
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", alert_name).lower()
    file_name = f"{safe_name}.yaml"
    path = os.path.join(PLAYBOOKS_DIR, file_name)

    if not os.path.abspath(path).startswith(os.path.abspath(PLAYBOOKS_DIR)):
        logger.error(f"Security Warning: Attempted path traversal for '{alert_name}'")
        return None

    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"No playbook found for '{alert_name}' at {path}")
        return None
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse playbook {path}: {e}")
        return None
