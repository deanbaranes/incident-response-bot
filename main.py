import os
import requests
import yaml
import base64
import google.generativeai as genai
from fastapi import FastAPI, Request
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

app = FastAPI()

# --- 1. Configuration Setup ---
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # Format: "username/repo"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# --- 2. Configure Gemini AI ---
# Using the latest available model from your list: gemini-2.5-flash
genai.configure(api_key=GEMINI_API_KEY, transport='rest')
ai_model = genai.GenerativeModel('models/gemini-2.5-flash')

def load_playbook_from_github(alert_name):
    """
    Fetches a YAML playbook from GitHub based on the alert name.
    Expects playbooks to be stored in the 'playbooks/' directory.
    """
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/playbooks/{alert_name.replace(' ', '_').lower()}.yaml"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = base64.b64decode(response.json()['content']).decode('utf-8')
            return yaml.safe_load(content)
        else:
            print(f"⚠️ Playbook not found on GitHub for: {alert_name} (Status: {response.status_code})")
            return None
    except Exception as e:
        print(f"❌ GitHub API Error: {e}")
        return None

def get_ai_insight(alertname, summary):
    """
    Sends alert data to Gemini AI to get professional DevOps troubleshooting steps.
    """
    prompt = (
        f"You are a Senior DevOps Engineer. An incident occurred: {alertname}.\n"
        f"Summary: {summary}.\n"
        f"Provide 3 concise troubleshooting bullet points in Hebrew."
    )
    try:
        response = ai_model.generate_content(prompt)
        if response and response.text:
            return response.text
        return "AI analysis unavailable at the moment."
    except Exception as e:
        return f"AI Error: {str(e)}"

def send_incident_email(subject, body):
    """
    Sends the final incident report via Gmail SMTP.
    """
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_SENDER # Sending to yourself for testing
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Email report sent successfully to {EMAIL_SENDER}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# --- 3. Webhook Endpoint ---
@app.post("/webhook")
async def handle_webhook(request: Request):
    """
    Main entry point for Grafana alerts. 
    Processes the alert, fetches playbook, gets AI insight, and sends email.
    """
    try:
        payload = await request.json()
        print("\n--- 🚨 NEW ALERT RECEIVED ---")
        
        # Normalize payload to list of alerts
        alerts = payload.get("alerts", [])
        if not isinstance(alerts, list):
            alerts = [alerts]

        for alert in alerts:
            labels = alert.get("labels", {})
            annotations = alert.get("annotations", {})
            
            alertname = labels.get("alertname", "Unknown Alert")
            summary = annotations.get("summary", "No description provided")
            
            print(f"Processing incident: {alertname}")

            # 1. Fetch Playbook from GitHub
            playbook = load_playbook_from_github(alertname)
            
            # 2. Get AI Insights from Gemini
            ai_insight = get_ai_insight(alertname, summary)
            
            # 3. Build the Report Body
            report = f"Incident Report: {alertname}\n" + "="*30 + "\n"
            report += f"Summary: {summary}\n\n"
            
            if playbook:
                report += f"📖 Playbook Found: {playbook.get('name', 'Default Playbook')}\n"
                report += "Predefined Steps (from GitHub):\n"
                for action in playbook.get("actions", []):
                    action_type = action.get('type', 'Step')
                    target = action.get('target', '')
                    report += f"- {action_type} {'[' + target + ']' if target else ''}\n"
            else:
                report += "⚠️ No specific GitHub playbook found for this alert.\n"
            
            report += f"\n🤖 AI Expert Analysis:\n{ai_insight}\n"
            
            # 4. Send the Email
            send_incident_email(f"PROD ALERT: {alertname}", report)

        return {"status": "success", "message": "Incident processed"}
    
    except Exception as e:
        print(f"🔥 Critical Webhook Error: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Running on port 5000 to match your previous tests
    uvicorn.run(app, host="0.0.0.0", port=5000)