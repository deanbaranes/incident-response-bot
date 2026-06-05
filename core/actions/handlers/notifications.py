import asyncio
import logging
import os
from typing import Dict, Any
from core.actions.base import ActionHandler
from core.actions.registry import ActionRegistry
from core.context import IncidentContext
from services.ai import get_ai_analysis
from services.email import send_email_report
from services.slack import send_slack_alert

logger = logging.getLogger(__name__)


class AiAnalysisHandler(ActionHandler):
    async def execute(
        self, action: Dict[str, Any], context: IncidentContext, alert: Dict[str, Any]
    ):
        logger.info("Running AI analysis...")
        # Since playbooks pass the whole playbook into `process_incident`, we might not have `instruction` here.
        # But we can get it from the action config if the playbook author puts it there, or just pass None for now.
        instruction = action.get("instruction")
        ai_output = await asyncio.to_thread(
            get_ai_analysis,
            context.alert_name,
            context.format_for_ai(),
            instruction=instruction,
        )
        context.ai_output = ai_output
        context.add_step("AI Analysis completed successfully.")


class SendEmailNotificationHandler(ActionHandler):
    async def execute(
        self, action: Dict[str, Any], context: IncidentContext, alert: Dict[str, Any]
    ):
        report_body = context.format_report()
        subject = f"Incident Report: {context.alert_name}"
        screenshot_path = context.screenshots[-1] if context.screenshots else None

        try:
            await asyncio.to_thread(
                send_email_report,
                subject,
                report_body,
                attachment_path=screenshot_path,
            )
            context.add_step("Notification: RCA report dispatched.")
            logger.info(f"Sent email for {context.alert_name}")
        except Exception as e:
            logger.error(f"Failed to send email report for {context.alert_name}: {e}")
            context.add_step(f"Notification: Failed to dispatch RCA report ({e}).")
        finally:
            if screenshot_path and os.path.exists(screenshot_path):
                try:
                    os.remove(screenshot_path)
                    logger.info(f"Cleaned up screenshot: {screenshot_path}")
                except Exception as cleanup_err:
                    logger.error(
                        f"Failed to clean up screenshot {screenshot_path}: {cleanup_err}"
                    )


class SendSlackNotificationHandler(ActionHandler):
    async def execute(
        self, action: Dict[str, Any], context: IncidentContext, alert: Dict[str, Any]
    ):
        logger.info("Sending Slack notification...")
        slack_message = (
            f"CRITICAL SUMMARY:\n{context.summary}\n\n"
            f"LIVE SYSTEM CONTEXT:\n{chr(10).join(context.enriched_data)}\n"
            f"AI RECOMMENDATIONS & RCA:\n{context.ai_output}\n"
        )
        screenshot_path = context.screenshots[-1] if context.screenshots else None
        await asyncio.to_thread(
            send_slack_alert,
            slack_message,
            title=f"Incident Alert: {context.alert_name}",
            screenshot_path=screenshot_path,
        )
        context.add_step("Notification: Slack alert dispatched.")


ActionRegistry.register("ai_analysis", AiAnalysisHandler())
ActionRegistry.register("send_notification", SendEmailNotificationHandler())
ActionRegistry.register("send_slack_notification", SendSlackNotificationHandler())
