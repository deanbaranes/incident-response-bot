import re
from config import GRAFANA_DASHBOARD_URL
from services.github import load_playbook
from services.grafana import capture_dashboard, fetch_grafana_metric
from services.ai import get_ai_analysis
from services.email import send_email_report

def process_incident(data):
    """
    Core Logic: Automated Incident Triage & Enrichment.
    This function acts as a 'First Responder' by:
    1. Identifying the alert and fetching its specific Playbook from GitHub.
    2. Executing declarative actions (Metrics, Screenshots, AI Analysis).
    3. Delivering a comprehensive report with visual evidence to the SRE team.
    """
    if "alerts" not in data:
        send_email_report("BOT TEST", "Responder Bot is Online and listening to Webhooks.")
        return

    for alert in data["alerts"]:
        # Skip resolved alerts to focus only on active incidents
        if alert.get("status") == "resolved": 
            continue
            
        alert_name = alert.get("labels", {}).get("alertname", "Unknown")
        summary = alert.get("annotations", {}).get("summary", "No details provided.")

        print(f"\n--- [Handling Alert] {alert_name} ---")
        
        # --- Step 1: Load Declarative Playbook from GitHub ---
        playbook = load_playbook(alert_name)
        
        # Variables to store enriched data through the execution flow
        enriched_data = f"Initial Summary: {summary}\n"
        execution_steps = ""
        ai_output = "No AI analysis performed."
        screenshot_path = None

        if playbook and "actions" in playbook:
            print(f"📖 Playbook Found: {playbook.get('name')}. Executing defined actions...")
            
            for action in playbook["actions"]:
                action_type = action.get("type")
                
                # --- ACTION: Capture Dashboard Screenshot ---
                # Requirement: Automated visual context for RCA.
                # Prioritizes the 'url' field in the YAML for incident-specific dashboards.
                if action_type == "capture_dashboard_screenshot":
                    # FALLBACK: If YAML doesn't specify a URL, use the default from .env
                    target_url = action.get("url") or GRAFANA_DASHBOARD_URL
                    
                    if target_url:
                        print(f"📸 [Action] Capturing Dashboard: {target_url}")
                        # We use the alert name in the filename to prevent overwriting during concurrent alerts
                        safe_alert_name = re.sub(r'[^a-zA-Z0-9_]', '_', alert_name)
                        unique_filename = f"snapshot_{safe_alert_name}.png"
                        screenshot_path = capture_dashboard(target_url, unique_filename)
                        
                        if screenshot_path:
                            execution_steps += f"✅ Visual Evidence: Dashboard captured from {target_url}\n"
                        else:
                            execution_steps += "❌ Visual Evidence: Failed to capture dashboard.\n"

                # --- ACTION: Fetch Live Metrics ---
                # Requirement: Enrich alert with real-time data points from Prometheus.
                elif action_type == "fetch_metrics":
                    target = action.get("target", "unknown metric")
                    # Support pulling exact PromQL query from YAML
                    prom_query = action.get("query")
                    
                    if not prom_query:
                        # Heuristics based on target name, or default to using target as query
                        if "cpu" in target.lower():
                            prom_query = "100 - (avg(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)"
                        elif "memory" in target.lower():
                            prom_query = "100 * (1 - ((avg_over_time(node_memory_MemFree_bytes[5m]) + avg_over_time(node_memory_Cached_bytes[5m]) + avg_over_time(node_memory_Buffers_bytes[5m])) / avg_over_time(node_memory_MemTotal_bytes[5m])))"
                        else:
                            prom_query = target  # Use the target as the direct raw query as a last resort
                            
                    metric_val = fetch_grafana_metric(target, prom_query)
                    enriched_data += f"- [LIVE METRIC] {target}: {metric_val}\n"
                    execution_steps += f"✅ Data Enrichment: {target} metrics retrieved successfully.\n"

                # --- ACTION: AI Root Cause Analysis ---
                # Requirement: Use LLM to provide first-responder insights.
                elif action_type == "ai_analysis":
                    print("🤖 [Action] Generating AI Insights with Vision...")
                    # Pass the unique screenshot path captured in the previous step
                    ai_output = get_ai_analysis(alert_name, enriched_data, screenshot_path)
                    execution_steps += "✅ AI Insights: Visual and textual analysis successfully integrated.\n"
                # --- ACTION: Send Notification ---
                # Requirement: Output report to the dedicated mailing list.
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
                    
                    # Sending email with the screenshot attachment (if captured)
                    subject = f"🚨 [CRITICAL] {alert_name} - Automated RCA Report"
                    send_email_report(subject, report_body, attachment_path=screenshot_path)
                    execution_steps += "✅ Notification: RCA report dispatched via SMTP.\n"
                    print(f"✉️ [Done] Report sent for {alert_name}")

        else:
            # Fallback Logic: If no specific YAML playbook is defined
            print(f"⚠️ No declarative playbook found for '{alert_name}'. Running generic triage (Text Only).")
            
            # Pass ONLY the text to the AI for minimal delay; no screenshots for fallback
            ai_output = get_ai_analysis(alert_name, summary, screenshot_path=None)
            
            fallback_subject = f"⚠️ [Alert] {alert_name} (No Playbook Found)"
            fallback_content = f"AI Insight (Text Analysis): {ai_output}\n\nPlease define a YAML playbook for this alert type if you want screenshots or deeper analysis."
            send_email_report(fallback_subject, fallback_content, attachment_path=None)

