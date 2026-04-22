import requests
import logging
import math
import re
from playwright.sync_api import sync_playwright
from config import GRAFANA_URL, GRAFANA_USERNAME, GRAFANA_TOKEN

logger = logging.getLogger(__name__)


# Fetches raw metric numbers from Prometheus based on a custom query
# This provides the AI and the final report with live data context
def fetch_grafana_metric(target_name, query):
    """Fetch live data from Prometheus API."""
    headers = {"Content-Type": "application/json"}

    auth = (GRAFANA_USERNAME, GRAFANA_TOKEN) if GRAFANA_USERNAME else None

    if not auth:
        headers["Authorization"] = f"Bearer {GRAFANA_TOKEN}"

    if not GRAFANA_URL:
        return "Error: GRAFANA_URL is not configured"

    base_url = GRAFANA_URL.rstrip("/")
    api_url = f"{base_url}/api/prom/api/v1/query"

    try:
        logger.info(f"Fetching metric: {target_name}")

        # Check 1: Time clipping - block long historical queries (DoS prevention)
        if re.search(r"\[[0-9]+[yMwd]\]", query):
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
            auth=auth,
            params={"query": safe_query, "timeout": "25s"},
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        data_results = result.get("data", {}).get("result", [])

        # Check 4: Guard Clause - ensure data exists before indexing to avoid IndexError crashes
        if not data_results:
            logger.warning(
                f"Prometheus query returned no data points for '{target_name}'."
            )
            return "No active data points found."

        # Check 5: Safely parse numerical values and handle Prometheus NaN/Inf edge cases
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

    except Exception as e:
        return f"Connection Failed: {str(e)}"


# Opens a headless browser to snap a picture of the Grafana dashboard
def capture_dashboard(url, output_path="dashboard.png"):
    """Capture a screenshot of the dashboard."""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.screenshot(path=output_path)
            browser.close()
            return output_path
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        return None
