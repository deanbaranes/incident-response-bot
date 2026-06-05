import asyncio
import logging
from typing import Dict, Any
from core.actions.base import ActionHandler
from core.actions.registry import ActionRegistry
from core.context import IncidentContext
from services.jira import create_jira_ticket
from services.pagerduty import create_pagerduty_incident
from services.opsgenie import send_opsgenie_alert
from services.grafana_oncall import send_grafana_oncall_alert

logger = logging.getLogger(__name__)


class CreateJiraTicketHandler(ActionHandler):
    async def execute(
        self, action: Dict[str, Any], context: IncidentContext, alert: Dict[str, Any]
    ):
        logger.info("Creating Jira ticket...")
        jira_desc = (
            f"CRITICAL SUMMARY:\n{context.summary}\n\n"
            f"LIVE SYSTEM CONTEXT:\n{chr(10).join(context.enriched_data)}\n"
            f"AI RECOMMENDATIONS & RCA:\n{context.ai_output}\n"
        )
        await asyncio.to_thread(
            create_jira_ticket,
            summary=f"[{context.alert_name}] Incident Alert",
            description=jira_desc,
        )
        context.add_step("Ticketing: Jira ticket created.")


class CreatePagerDutyIncidentHandler(ActionHandler):
    async def execute(
        self, action: Dict[str, Any], context: IncidentContext, alert: Dict[str, Any]
    ):
        logger.info("Triggering PagerDuty...")
        await asyncio.to_thread(
            create_pagerduty_incident,
            title=f"Incident: {context.alert_name}",
            message=context.summary,
            alert_name=context.alert_name,
        )
        context.add_step("Notification: PagerDuty triggered.")


class SendOpsGenieAlertHandler(ActionHandler):
    async def execute(
        self, action: Dict[str, Any], context: IncidentContext, alert: Dict[str, Any]
    ):
        logger.info("Triggering OpsGenie...")
        await asyncio.to_thread(
            send_opsgenie_alert,
            title=f"Incident: {context.alert_name}",
            message=context.summary,
            alert_name=context.alert_name,
        )
        context.add_step("Notification: OpsGenie triggered.")


class SendGrafanaOnCallAlertHandler(ActionHandler):
    async def execute(
        self, action: Dict[str, Any], context: IncidentContext, alert: Dict[str, Any]
    ):
        logger.info("Triggering Grafana OnCall...")
        await asyncio.to_thread(
            send_grafana_oncall_alert,
            title=f"Incident: {context.alert_name}",
            message=context.summary,
            alert_name=context.alert_name,
        )
        context.add_step("Notification: Grafana OnCall triggered.")


ActionRegistry.register("create_jira_ticket", CreateJiraTicketHandler())
ActionRegistry.register("create_pagerduty_incident", CreatePagerDutyIncidentHandler())
ActionRegistry.register("send_opsgenie_alert", SendOpsGenieAlertHandler())
ActionRegistry.register("send_grafana_oncall_alert", SendGrafanaOnCallAlertHandler())
