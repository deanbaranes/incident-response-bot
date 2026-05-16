import logging
import requests
from requests.auth import HTTPBasicAuth
from config import JIRA_BASE_URL, JIRA_USER, JIRA_API_TOKEN, JIRA_PROJECT_KEY

logger = logging.getLogger(__name__)

def create_jira_ticket(summary: str, description: str, issue_type: str = "Task", priority: str = "High") -> bool:
    """Create an incident ticket in Jira."""
    if not all([JIRA_BASE_URL, JIRA_USER, JIRA_API_TOKEN, JIRA_PROJECT_KEY]):
        logger.info(f"MOCK JIRA TICKET: [{JIRA_PROJECT_KEY or 'KAN'}] {summary}")
        return True

    url = f"{JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue"
    auth = HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }
                ]
            },
            "issuetype": {"name": issue_type}
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, auth=auth, timeout=15)
        response.raise_for_status()
        issue_key = response.json().get('key')
        logger.info(f"Successfully created Jira ticket: {issue_key}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to create Jira ticket: {e}")
        if e.response is not None:
            logger.error(f"Jira API Response: {e.response.text}")
        return False
