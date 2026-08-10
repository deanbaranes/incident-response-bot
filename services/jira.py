import logging

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.settings import settings

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.RequestError),
    reraise=True,
)
async def create_jira_ticket(
    summary: str, description: str, issue_type: str = "Task", priority: str = "High"
) -> bool:
    """Create an incident ticket in Jira."""
    if (
        not settings.JIRA_BASE_URL
        or not settings.JIRA_USER
        or not settings.JIRA_API_TOKEN
        or not settings.JIRA_PROJECT_KEY
    ):
        logger.info(
            f"MOCK JIRA TICKET: [{settings.JIRA_PROJECT_KEY or 'KAN'}] {summary}"
        )
        return True

    url = f"{settings.JIRA_BASE_URL.rstrip('/')}/rest/api/3/issue"
    auth = (settings.JIRA_USER, settings.JIRA_API_TOKEN)
    headers = {"Accept": "application/json"}

    payload = {
        "fields": {
            "project": {"key": settings.JIRA_PROJECT_KEY},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": issue_type},
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url, json=payload, headers=headers, auth=auth, timeout=15.0
        )
        response.raise_for_status()
        issue_key = response.json().get("key")

    logger.info(f"Successfully created Jira ticket: {issue_key}")
    return True
