import os
import requests
import yaml
import base64
import google.generativeai as genai
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.sync_api import sync_playwright
import time
from email.mime.base import MIMEBase
from email import encoders
import PIL.Image
import re

# Initialize Environment Variables
load_dotenv()

app = FastAPI()

# --- Configuration ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_USERNAME = os.getenv("GRAFANA_USERNAME")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")
GRAFANA_DASHBOARD_URL = os.getenv("GRAFANA_DASHBOARD_URL")

# Check required environment variables to prevent crashes
missing_envs = [name for name in ["GITHUB_TOKEN", "GITHUB_REPO", "GEMINI_API_KEY", "EMAIL_SENDER", "EMAIL_PASSWORD", "GRAFANA_TOKEN"] if not os.getenv(name)]
if missing_envs:
    print(f"⚠️ WARNING: The following essential environment variables are missing: {', '.join(missing_envs)}")

# --- AI Setup ---
genai.configure(api_key=GEMINI_API_KEY, transport='rest')
ai_model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- Helper Functions ---

def fetch_grafana_metric(target_name, query):
    """Fetch live data from Grafana Cloud Prometheus API."""
    headers = {
        "Content-Type": "application/json"
    }
    
    # Grafana Cloud Prometheus requires Basic Auth (Username: Instance ID, Password: API Token)
    auth = (GRAFANA_USERNAME, GRAFANA_TOKEN) if GRAFANA_USERNAME else None
    
    # Fallback for local grafana
    if not auth:
        headers["Authorization"] = f"Bearer {GRAFANA_TOKEN}"
        
    api_url = "https://prometheus-prod-58-prod-eu-central-0.grafana.net/api/prom/api/v1/query"
    
    try:
        print(f"🔍 Fetching live data for: {target_name} with query: {query[:50]}...")
        response = requests.get(
            api_url,
            headers=headers,
            auth=auth,
            params={"query": query},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("data", {}).get("result"):
                value = result["data"]["result"][0]["value"][1]
                return f"{float(value):.1f}%"
            return "No active data points found."
        return f"Error: API returned status {response.status_code}"
    except Exception as e:
        return f"Connection Failed: {str(e)}"

        
def load_playbook(alert_name):
    """Download the relevant YAML playbook from GitHub."""
    file_name = alert_name.replace(' ', '_').lower()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/playbooks/{file_name}.yaml"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = base64.b64decode(response.json()['content']).decode('utf-8')
            return yaml.safe_load(content)
        return None
    except Exception as e:
        print(f"❌ GitHub Error: {e}")
        return None

def get_ai_analysis(alert_name, context, screenshot_path=None):
    """Use Gemini AI to generate troubleshooting steps based on text and visual dashboard data."""
    
    # Generic and flexible prompt for any dashboard layout
    prompt = (
        f"You are an expert Site Reliability Engineer (SRE).\n"
        f"Analyze the following incident using the provided context and the attached dashboard screenshot.\n\n"
        f"SYSTEM ALERT: {alert_name}\n"
        f"CONTEXT: {context}\n\n"
        "INSTRUCTIONS:\n"
        "1. Visual Inspection: Scan the screenshot for anomalies (RED/ORANGE panels or extreme spikes).\n"
        "2. Identification: Identify titles of problematic panels directly from the image text.\n"
        "3. Correlation: Determine if visual evidence confirms the alert or suggests a different root cause.\n"
        "4. Action Plan: Provide 3 professional troubleshooting steps based on this combined analysis."
    )
    
    try:
        # If a screenshot exists, perform multi-modal analysis (Vision + Text)
        if screenshot_path and os.path.exists(screenshot_path):
            img = PIL.Image.open(screenshot_path)
            response = ai_model.generate_content([prompt, img])
        else:
            # Fallback to text-only analysis if no image is available
            response = ai_model.generate_content(prompt)
            
        return response.text if response else "AI Analysis Failed."
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return "AI Service Unavailable or Visual Analysis Failed."

        
def send_email_report(subject, content, attachment_path=None):
    """Send the final report via SMTP."""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_SENDER
        msg['Subject'] = subject
        msg.attach(MIMEText(content, 'plain'))
        
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
            
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(attachment_path)}",
            )
            msg.attach(part)
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Report sent successfully.")
    except Exception as e:
        print(f"❌ Email Error: {e}")

def capture_dashboard(url, output_path="dashboard.png"):
    """Capture a screenshot of the Grafana dashboard."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.new_page()
            page.goto(url, wait_until="networkidle")
            time.sleep(5)  # Allow graphs to render
            page.screenshot(path=output_path)
            browser.close()
            return output_path
    except Exception as e:
        print(f"❌ Failed to capture screenshot: {e}")
        return None

# --- Core Logic ---

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

# --- API Routes ---

@app.post("/webhook")
async def webhook_receiver(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    background_tasks.add_task(process_incident, payload)
    return {"status": "processing"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)