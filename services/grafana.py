import requests
import time
from playwright.sync_api import sync_playwright
from config import GRAFANA_URL, GRAFANA_USERNAME, GRAFANA_TOKEN

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
        
    # Dynamically build Prometheus API URL from environment variable
    base_url = GRAFANA_URL.rstrip('/') if GRAFANA_URL else "https://prometheus-prod-58-prod-eu-central-0.grafana.net"
    api_url = f"{base_url}/api/prom/api/v1/query"
    
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
            time.sleep(10)  # Allow graphs to render
            page.screenshot(path=output_path)
            browser.close()
            return output_path
    except Exception as e:
        print(f"❌ Failed to capture screenshot: {e}")
        return None
