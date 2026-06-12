import logging
import asyncio
import os
from services.playbooks import load_playbook
from core.log_config import incident_id_var
from core.context import IncidentContext
from core.actions.registry import ActionRegistry

# Import handlers to trigger registration

from services.email import send_email_report
from services.ai import get_ai_analysis

logger = logging.getLogger(__name__)


async def process_incident(data, incident_id=None):
    """Process incoming webhook alerts and execute incident response playbooks using ActionRegistry."""
    if incident_id:
        incident_id_var.set(incident_id)

    if "alerts" not in data:
        await asyncio.to_thread(
            send_email_report,
            "BOT TEST",
            "Responder Bot is Online and listening to Webhooks.",
        )
        return

    for alert in data["alerts"]:
        if alert.get("status") == "resolved":
            continue

        alert_name = alert.get("labels", {}).get("alertname", "Unknown")
        summary = alert.get("annotations", {}).get("summary", "No details provided.")

        logger.info(f"Processing alert: {alert_name}")

        playbook = load_playbook(alert_name)

        context = IncidentContext(
            incident_id=incident_id or incident_id_var.get("unknown"),
            alert_name=alert_name,
            summary=summary,
        )

        if playbook and "actions" in playbook:
            logger.info(f"Found playbook: {playbook.get('name')}")

            for action in playbook["actions"]:
                action_type = action.get("type")
                handler = ActionRegistry.get_handler(action_type)

                if handler:
                    try:
                        await handler.execute(action, context, alert)
                    except Exception as e:
                        logger.error(f"Error executing action {action_type}: {e}")
                        context.add_step(f"Error executing {action_type}: {e}")
                else:
                    logger.warning(f"Unknown action type in playbook: {action_type}")
                    context.add_step(
                        f"Warning: Unknown action type '{action_type}' skipped."
                    )
        else:
            logger.warning(f"No playbook for '{alert_name}'. Using fallback.")
            ai_output = await asyncio.to_thread(get_ai_analysis, alert_name, summary)
            fallback_subject = f"[Alert] {alert_name} (No Playbook Found)"
            fallback_content = f"AI Insight (Text Analysis): {ai_output}\n\nPlease define a YAML playbook for this alert type if you want screenshots or deeper analysis."
            await asyncio.to_thread(
                send_email_report,
                fallback_subject,
                fallback_content,
                attachment_path=None,
            )

        # Ensure screenshots are cleaned up regardless of success/failure of individual actions
        for screenshot_path in context.screenshots:
            if os.path.exists(screenshot_path):
                try:
                    os.remove(screenshot_path)
                    logger.info(f"Cleaned up screenshot: {screenshot_path}")
                except Exception as e:
                    logger.error(
                        f"Failed to clean up screenshot {screenshot_path}: {e}"
                    )
