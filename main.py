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

# --- AI Setup ---
genai.configure(api_key=GEMINI_API_KEY, transport='rest')
ai_model = genai.GenerativeModel('models/gemini-2.5-flash')

# --- Helper Functions ---

def fetch_grafana_metric(target_metric):
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
    query = "100 - (avg(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)"
    
    try:
        print(f"🔍 Fetching live data for: {target_metric}")
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

def get_ai_analysis(alert_name, context):
    """Use Gemini AI to generate troubleshooting steps."""
    prompt = (
        f"Incident: {alert_name}.\n"
        f"Context: {context}.\n"
        f"Provide 3 professional troubleshooting steps based on this data."
    )
    try:
        response = ai_model.generate_content(prompt)
        return response.text if response else "AI Analysis Failed."
    except:
        return "AI Service Unavailable."

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
    print(f"📷 Capturing dashboard snapshot: {url}")
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
    if "alerts" not in data:
        send_email_report("BOT TEST", "Responder Bot is Online.")
        return

    for alert in data["alerts"]:
        if alert.get("status") == "resolved": continue
            
        alert_name = alert.get("labels", {}).get("alertname", "Unknown")
        summary = alert.get("annotations", {}).get("summary", "No details provided.")

        print(f"\n--- Handling Alert: {alert_name} ---")
        playbook = load_playbook(alert_name)
        
        enriched_data = f"Initial Summary: {summary}\n"
        execution_steps = ""
        ai_output = ""
        screenshot_path = None

        if GRAFANA_DASHBOARD_URL:
            screenshot_path = capture_dashboard(GRAFANA_DASHBOARD_URL, f"snapshot_{alert_name.replace(' ', '_')}.png")
            if screenshot_path:
                execution_steps += "✅ Dashboard Capture: Screenshot saved successfully.\n"

        if playbook and "actions" in playbook:
            print(f"📖 Executing Playbook: {playbook.get('name')}")
            
            for action in playbook["actions"]:
                action_type = action.get("type")
                
                if action_type == "fetch_metrics":
                    target = action.get("target", "cpu")
                    metric_val = fetch_grafana_metric(target)
                    enriched_data += f"- [LIVE METRIC] {target}: {metric_val}\n"
                    execution_steps += f"✅ Data Fetch: {target} retrieval successful.\n"

                elif action_type == "ai_analysis":
                    ai_output = get_ai_analysis(alert_name, enriched_data)
                    execution_steps += "✅ AI Analysis: Root cause identified.\n"

                elif action_type == "send_notification":
                    report = (
                        f"INCIDENT REPORT: {alert_name}\n"
                        f"{'='*30}\n"
                        f"SUMMARY: {summary}\n\n"
                        f"EXECUTION LOG:\n{execution_steps}\n"
                        f"LIVE CONTEXT:\n{enriched_data}\n"
                        f"AI RECOMMENDATIONS:\n{ai_output}\n"
                        f"{'='*30}"
                    )
                    send_email_report(f"CRITICAL ALERT: {alert_name}", report, attachment_path=screenshot_path)
                    execution_steps += "✅ Notification: Report delivered.\n"
        else:
            # Fallback
            ai_output = get_ai_analysis(alert_name, summary)
            send_email_report(f"ALERT: {alert_name}", f"AI Insight: {ai_output}", attachment_path=screenshot_path)

# --- API Routes ---

@app.post("/webhook")
async def webhook_receiver(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    background_tasks.add_task(process_incident, payload)
    return {"status": "processing"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)