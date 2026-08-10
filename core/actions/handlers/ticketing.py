import logging
from typing import Any

from core.actions.base import ActionHandler
from core.actions.registry import ActionRegistry
from core.context import IncidentContext
from services.grafana_oncall import send_grafana_oncall_alert
from services.jira import create_jira_ticket
from services.opsgenie import send_opsgenie_alert
from services.pagerduty import create_pagerduty_incident

logger = logging.getLogger(__name__)


class CreateJiraTicketHandler(ActionHandler):
    async def execute(
        self, action: dict[str, Any], context: IncidentContext, alert: dict[str, Any]
    ):
        logger.info("Creating Jira ticket...")
        jira_desc = (
            f"CRITICAL SUMMARY:\n{context.summary}\n\n"
            f"LIVE SYSTEM CONTEXT:\n{chr(10).join(context.enriched_data)}\n"
            f"AI RECOMMENDATIONS & RCA:\n{context.ai_output}\n"
        )
        await create_jira_ticket(
            summary=f"[{context.alert_name}] Incident Alert",
            description=jira_desc,
        )
        context.add_step("Ticketing: Jira ticket created.")


class CreatePagerDutyIncidentHandler(ActionHandler):
    async def execute(
        self, action: dict[str, Any], context: IncidentContext, alert: dict[str, Any]
    ):
        logger.info("Triggering PagerDuty...")
        severity = action.get("severity", "critical")
        title = action.get("title", f"Incident: {context.alert_name}")
        await create_pagerduty_incident(
            title=title,
            message=context.summary,
            alert_name=context.alert_name,
            severity=severity,
        )
        context.add_step("Notification: PagerDuty triggered.")


class SendOpsGenieAlertHandler(ActionHandler):
    async def execute(
        self, action: dict[str, Any], context: IncidentContext, alert: dict[str, Any]
    ):
        logger.info("Triggering OpsGenie...")
        priority = action.get("priority", "P3")
        title = action.get("title", f"Incident: {context.alert_name}")
        await send_opsgenie_alert(
            title=title,
            message=context.summary,
            alert_name=context.alert_name,
            priority=priority,
        )
        context.add_step("Notification: OpsGenie triggered.")


class SendGrafanaOnCallAlertHandler(ActionHandler):
    async def execute(
        self, action: dict[str, Any], context: IncidentContext, alert: dict[str, Any]
    ):
        logger.info("Triggering Grafana OnCall...")
        title = action.get("title", f"Incident: {context.alert_name}")
        await send_grafana_oncall_alert(
            title=title,
            message=context.summary,
            alert_name=context.alert_name,
        )
        context.add_step("Notification: Grafana OnCall triggered.")


ActionRegistry.register("create_jira_ticket", CreateJiraTicketHandler())
ActionRegistry.register("create_pagerduty_incident", CreatePagerDutyIncidentHandler())
ActionRegistry.register("send_opsgenie_alert", SendOpsGenieAlertHandler())
ActionRegistry.register("send_grafana_oncall_alert", SendGrafanaOnCallAlertHandler())
