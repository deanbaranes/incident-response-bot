import requests
import logging
import math
from playwright.sync_api import sync_playwright
from config import GRAFANA_URL, GRAFANA_TOKEN

logger = logging.getLogger(__name__)


# Fetches raw metric numbers from Prometheus based on a custom query
# This provides the AI and the final report with live data context
def fetch_grafana_metric(target_name, query):
    """Fetch live data from Prometheus API."""
    # Use Bearer authentication with the Grafana Token (required for proxy access)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GRAFANA_TOKEN}"
    }

    if not GRAFANA_URL:
        return "Error: GRAFANA_URL is not configured"

    base_url = GRAFANA_URL.rstrip("/")
    # Using the Grafana Proxy (Data Source 8) to bypass direct Prometheus authentication issues
    api_url = f"{base_url}/api/datasources/proxy/8/api/v1/query"

    try:
        logger.info(f"Fetching metric: {target_name}")

        # Check 1: Input Validation - prevent massive time range queries
        if "range" in query or "1y" in query:
            logger.warning(
                f"BLOCKED: Query for '{target_name}' exceeds maximum allowed time range."
            )
            return "Blocked: Time range too large."

        # Check 2: Sanitize query string to prevent basic injections
        safe_query = query.replace(";", "").strip()

        # Check 3: Double Timeout - API aborts at 25s, Python waits 30s to catch the status gracefully
        response = requests.get(
            api_url,
            headers=headers,
            params={"query": safe_query, "timeout": "25s"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        data_results = data.get("data", {}).get("result", [])
        if not data_results:
            logger.warning(f"Prometheus query returned no data points for '{target_name}'.")
            return "No active data points found."

        try:
            value_str = data_results[0]["value"][1]
            if str(value_str).lower() == "nan":
                return "N/A (No numeric data)"

            val_float = float(value_str)
            if math.isnan(val_float) or math.isinf(val_float):
                return "N/A (Invalid numeric metric)"

            return f"{val_float:.1f}%"
        except (IndexError, KeyError, TypeError, ValueError):
            logger.error(
                f"Malformed data structure received for '{target_name}' from Prometheus."
            )
            return "Invalid data format received."

    except requests.exceptions.RequestException as e:
        logger.error(f"Connection Failed for '{target_name}': {e}")
        return f"Connection Failed: {e}"
    except Exception as e:
        logger.error(f"Unknown error fetching '{target_name}': {e}")
        return "Unexpected error."


# Captures a snapshot of a Grafana dashboard using Playwright
# Uses a smart wait for the '.panel-content' to ensure charts are rendered
def capture_dashboard(url, output_path):
    """Take a screenshot of a Grafana dashboard."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded")
            try:
                # Wait specifically for Grafana panels to render content
                page.wait_for_selector(".panel-content", state="visible", timeout=15000)
            except Exception:
                logger.warning("Panel content not found within timeout, taking screenshot as-is.")

            page.screenshot(path=output_path)
            browser.close()
            return output_path
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        return None
