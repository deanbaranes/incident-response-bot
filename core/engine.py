import os
import re
import logging
import asyncio
from config import GRAFANA_DASHBOARD_URL
from services.playbooks import load_playbook
from services.grafana import capture_dashboard, fetch_grafana_metric
from services.ai import get_ai_analysis
from services.email import send_email_report
from services.slack import send_slack_alert
from services.jira import create_jira_ticket
from services.pagerduty import create_pagerduty_incident
from services.opsgenie import send_opsgenie_alert
from services.grafana_oncall import send_grafana_oncall_alert
from core.log_config import incident_id_var

logger = logging.getLogger(__name__)


async def process_incident(data, incident_id=None):
    """Process incoming webhook alerts and execute incident response playbooks."""
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

        enriched_data = f"Summary: {summary}\n"
        execution_steps = ""
        ai_output = "No AI analysis performed."
        screenshot_path = None
        playbook_instruction = playbook.get("instruction") if playbook else None

        if playbook and "actions" in playbook:
            logger.info(f"Found playbook: {playbook.get('name')}")

            for action in playbook["actions"]:
                action_type = action.get("type")

                # Capture Dashboard Screenshot
                if action_type == "capture_dashboard_screenshot":
                    target_url = action.get("url") or GRAFANA_DASHBOARD_URL

                    if target_url:
                        logger.info(f"Capturing dashboard: {target_url}")
                        safe_alert_name = re.sub(r"[^a-zA-Z0-9_]", "_", alert_name)
                        current_id = incident_id or incident_id_var.get("unknown")
                        unique_filename = f"snapshot_{safe_alert_name}_{current_id}.png"
                        screenshot_path = await asyncio.to_thread(
                            capture_dashboard, target_url, unique_filename
                        )

                        if screenshot_path:
                            execution_steps += f"Visual Evidence: Dashboard captured from {target_url}\n"
                        else:
                            execution_steps += (
                                "Visual Evidence: Failed to capture dashboard.\n"
                            )

                # Fetch Live Metrics
                elif action_type == "fetch_metrics":
                    target = action.get("target", "unknown metric")
                    prom_query = action.get("query")

                    if not prom_query:
                        if "cpu" in target.lower():
                            prom_query = "100 - (avg(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)"
                        elif "memory" in target.lower():
                            prom_query = "100 * (1 - ((avg_over_time(node_memory_MemFree_bytes[5m]) + avg_over_time(node_memory_Cached_bytes[5m]) + avg_over_time(node_memory_Buffers_bytes[5m])) / avg_over_time(node_memory_MemTotal_bytes[5m])))"
                        else:
                            prom_query = target

                    metric_val = await asyncio.to_thread(
                        fetch_grafana_metric, target, prom_query
                    )
                    enriched_data += f"- [Metric] {target}: {metric_val}\n"
                    execution_steps += f"Enrichment: {target} metrics retrieved.\n"

                elif action_type == "ai_analysis":
                    logger.info("Running AI analysis...")
                    ai_output = await asyncio.to_thread(
                        get_ai_analysis,
                        alert_name,
                        enriched_data,
                        instruction=playbook_instruction,
                    )
                    execution_steps += "AI Analysis completed successfully.\n"

                # Send Notification
                elif action_type == "send_notification":
                    report_body = (
                        f"INCIDENT REPORT: {alert_name}\n"
                        f"{'=' * 40}\n"
                        f"CRITICAL SUMMARY:\n{summary}\n\n"
                        f"AUTOMATED EXECUTION LOG:\n{execution_steps}\n"
                        f"LIVE SYSTEM CONTEXT:\n{enriched_data}\n"
                        f"AI RECOMMENDATIONS & RCA:\n{ai_output}\n"
                        f"{'=' * 40}\n"
                        f"Status: This report was generated automatically by the AI-Responder Bot."
                    )

                    subject = f"Incident Report: {alert_name}"
                    try:
                        await asyncio.to_thread(
                            send_email_report,
                            subject,
                            report_body,
                            attachment_path=screenshot_path,
                        )
                        execution_steps += "Notification: RCA report dispatched.\n"
                        logger.info(f"Sent email for {alert_name}")
                    except Exception as e:
                        logger.error(
                            f"Failed to send email report for {alert_name}: {e}"
                        )
                        execution_steps += (
                            f"Notification: Failed to dispatch RCA report ({e}).\n"
                        )
                    finally:
                        if screenshot_path and await asyncio.to_thread(
                            os.path.exists, screenshot_path
                        ):
                            try:
                                await asyncio.to_thread(os.remove, screenshot_path)
                                logger.info(f"Cleaned up screenshot: {screenshot_path}")
                            except Exception as cleanup_err:
                                logger.error(
                                    f"Failed to clean up screenshot {screenshot_path}: {cleanup_err}"
                                )

                # Send Slack Notification
                elif action_type == "send_slack_notification":
                    logger.info("Sending Slack notification...")
                    slack_message = (
                        f"CRITICAL SUMMARY:\n{summary}\n\n"
                        f"LIVE SYSTEM CONTEXT:\n{enriched_data}\n"
                        f"AI RECOMMENDATIONS & RCA:\n{ai_output}\n"
                    )
                    await asyncio.to_thread(
                        send_slack_alert,
                        slack_message,
                        title=f"Incident Alert: {alert_name}",
                        screenshot_path=screenshot_path,
                    )
                    execution_steps += "Notification: Slack alert dispatched.\n"

                # Create Jira Ticket
                elif action_type == "create_jira_ticket":
                    logger.info("Creating Jira ticket...")
                    jira_desc = (
                        f"CRITICAL SUMMARY:\n{summary}\n\n"
                        f"LIVE SYSTEM CONTEXT:\n{enriched_data}\n"
                        f"AI RECOMMENDATIONS & RCA:\n{ai_output}\n"
                    )
                    await asyncio.to_thread(
                        create_jira_ticket,
                        summary=f"[{alert_name}] Incident Alert",
                        description=jira_desc,
                    )
                    execution_steps += "Ticketing: Jira ticket created.\n"

                # Create PagerDuty Incident
                elif action_type == "create_pagerduty_incident":
                    logger.info("Triggering PagerDuty...")
                    await asyncio.to_thread(
                        create_pagerduty_incident,
                        title=f"Incident: {alert_name}",
                        message=summary,
                        alert_name=alert_name,
                    )
                    execution_steps += "Notification: PagerDuty triggered.\n"

                # Create OpsGenie Alert
                elif action_type == "send_opsgenie_alert":
                    logger.info("Triggering OpsGenie...")
                    await asyncio.to_thread(
                        send_opsgenie_alert,
                        title=f"Incident: {alert_name}",
                        message=summary,
                        alert_name=alert_name,
                    )
                    execution_steps += "Notification: OpsGenie triggered.\n"

                # Send Grafana OnCall Alert
                elif action_type == "send_grafana_oncall_alert":
                    logger.info("Triggering Grafana OnCall...")
                    await asyncio.to_thread(
                        send_grafana_oncall_alert,
                        title=f"Incident: {alert_name}",
                        message=summary,
                        alert_name=alert_name,
                    )
                    execution_steps += "Notification: Grafana OnCall triggered.\n"

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
