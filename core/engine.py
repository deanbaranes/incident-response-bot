import os
import re
import logging
from config import GRAFANA_DASHBOARD_URL
from services.playbooks import load_playbook
from services.grafana import capture_dashboard, fetch_grafana_metric
from services.ai import get_ai_analysis
from services.email import send_email_report

logger = logging.getLogger(__name__)

def process_incident(data):
    """Process incoming webhook alerts and execute incident response playbooks."""
    if "alerts" not in data:
        send_email_report("BOT TEST", "Responder Bot is Online and listening to Webhooks.")
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

        if playbook and "actions" in playbook:
            logger.info(f"Found playbook: {playbook.get('name')}")
            
            for action in playbook["actions"]:
                action_type = action.get("type")
                
                # Capture Dashboard Screenshot
                if action_type == "capture_dashboard_screenshot":
                    target_url = action.get("url") or GRAFANA_DASHBOARD_URL
                    
                    if target_url:
                        logger.info(f"Capturing dashboard: {target_url}")
                        safe_alert_name = re.sub(r'[^a-zA-Z0-9_]', '_', alert_name)
                        unique_filename = f"snapshot_{safe_alert_name}.png"
                        screenshot_path = capture_dashboard(target_url, unique_filename)
                        
                        if screenshot_path:
                            execution_steps += f"Visual Evidence: Dashboard captured from {target_url}\n"
                        else:
                            execution_steps += "Visual Evidence: Failed to capture dashboard.\n"

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
                            
                    metric_val = fetch_grafana_metric(target, prom_query)
                    enriched_data += f"- [Metric] {target}: {metric_val}\n"
                    execution_steps += f"Enrichment: {target} metrics retrieved.\n"

                # AI Root Cause Analysis
                elif action_type == "ai_analysis":
                    logger.info("Running AI analysis...")
                    ai_output = get_ai_analysis(alert_name, enriched_data, screenshot_path)
                    execution_steps += "AI Analysis completed successfully.\n"

                # Send Notification
                elif action_type == "send_notification":
                    report_body = (
                        f"INCIDENT REPORT: {alert_name}\n"
                        f"{'='*40}\n"
                        f"CRITICAL SUMMARY:\n{summary}\n\n"
                        f"AUTOMATED EXECUTION LOG:\n{execution_steps}\n"
                        f"LIVE SYSTEM CONTEXT:\n{enriched_data}\n"
                        f"AI RECOMMENDATIONS & RCA:\n{ai_output}\n"
                        f"{'='*40}\n"
                        f"Status: This report was generated automatically by the AI-Responder Bot."
                    )

                    subject = f"Incident Report: {alert_name}"
                    try:
                        send_email_report(subject, report_body, attachment_path=screenshot_path)
                        execution_steps += "Notification: RCA report dispatched.\n"
                        logger.info(f"Sent email for {alert_name}")
                    finally:
                        if screenshot_path and os.path.exists(screenshot_path):
                            os.remove(screenshot_path)
                            logger.info(f"Cleaned up screenshot: {screenshot_path}")

        else:
            logger.warning(f"No playbook for '{alert_name}'. Using fallback.")
            ai_output = get_ai_analysis(alert_name, summary, screenshot_path=None)
            
            fallback_subject = f"[Alert] {alert_name} (No Playbook Found)"
            fallback_content = f"AI Insight (Text Analysis): {ai_output}\n\nPlease define a YAML playbook for this alert type if you want screenshots or deeper analysis."
            send_email_report(fallback_subject, fallback_content, attachment_path=None)
