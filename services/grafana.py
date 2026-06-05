import requests
import logging
import math
import urllib.parse
import re
from playwright.sync_api import sync_playwright
from config import GRAFANA_URL, GRAFANA_TOKEN, GRAFANA_PROMETHEUS_DATASOURCE_ID

logger = logging.getLogger(__name__)


# Fetches raw metric numbers from Prometheus based on a custom query
# This provides the AI and the final report with live data context
def fetch_grafana_metric(target_name, query):
    """Fetch live data from Prometheus API."""
    # Use Bearer authentication with the Grafana Token (required for proxy access)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GRAFANA_TOKEN}",
    }

    if not GRAFANA_URL:
        return "Error: GRAFANA_URL is not configured"

    base_url = GRAFANA_URL.rstrip("/")
    # Using the Grafana Proxy to bypass direct Prometheus authentication issues
    api_url = f"{base_url}/api/datasources/proxy/{GRAFANA_PROMETHEUS_DATASOURCE_ID}/api/v1/query"

    try:
        logger.info(f"Fetching metric: {target_name}")

        # Check 1: Input Validation - prevent massive time range queries using Regex
        # Blocks any range vector using 'd' (days), 'w' (weeks), or 'y' (years) e.g., [1d], [2w]
        if re.search(r"\[\s*\d+\s*[ywd]\s*\]", query, re.IGNORECASE):
            logger.warning(
                f"BLOCKED: Query for '{target_name}' exceeds maximum allowed time range."
            )
            return "Blocked: Time range too large (only hours/minutes allowed)."

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
            logger.warning(
                f"Prometheus query returned no data points for '{target_name}'."
            )
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
    # SSRF Protection: Strict domain whitelisting
    try:
        parsed_target = urllib.parse.urlparse(url)
        parsed_base = urllib.parse.urlparse(GRAFANA_URL)

        ALLOWED_DOMAINS = [parsed_base.hostname]

        if not parsed_target.hostname or parsed_target.hostname not in ALLOWED_DOMAINS:
            logger.error(
                f"SSRF Protection triggered: blocked access to un-whitelisted host '{parsed_target.hostname}'"
            )
            return None
    except Exception as e:
        logger.error(f"Invalid URL provided for dashboard: {e}")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                # Wait specifically for Grafana panels to render content
                page.wait_for_selector(".panel-content", state="visible", timeout=15000)
            except Exception:
                logger.warning(
                    "Panel content not found within timeout, taking screenshot as-is."
                )

            page.screenshot(path=output_path)
            browser.close()
            return output_path
    except Exception as e:
        logger.error(f"Failed to capture screenshot: {e}")
        return None


def execute_grafana_query(datasource_uid, query, time_from="now-15m", time_to="now"):
    """Execute a generic query against any Grafana datasource using the /api/ds/query endpoint."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GRAFANA_TOKEN}",
    }

    if not GRAFANA_URL:
        return "Error: GRAFANA_URL is not configured"

    base_url = GRAFANA_URL.rstrip("/")
    api_url = f"{base_url}/api/ds/query"

    payload = {
        "queries": [
            {
                "refId": "A",
                "datasource": {"uid": datasource_uid},
                "expr": query,
            }
        ],
        "from": time_from,
        "to": time_to,
    }

    try:
        logger.info(f"Executing Grafana query against datasource: {datasource_uid}")

        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", {})
        query_a_result = results.get("A", {})
        frames = query_a_result.get("frames", [])

        if not frames:
            return "Grafana Query returned successfully with NO data/rows found."

        # Parse frames to text to save context window space
        formatted_output = []
        for frame in frames:
            schema_fields = frame.get("schema", {}).get("fields", [])
            column_names = [f.get("name", "unknown") for f in schema_fields]

            data_values = frame.get("data", {}).get("values", [])

            if not column_names or not data_values:
                continue

            # data_values is typically a list of columns (each column is a list of row values)
            # e.g. [[t1, t2], [v1, v2]]
            # We want to transpose it to rows
            try:
                rows = list(zip(*data_values))
                if not rows:
                    continue

                formatted_output.append(f"Columns: {', '.join(column_names)}")
                for i, row in enumerate(rows):
                    row_str = " | ".join(str(val) for val in row)
                    formatted_output.append(row_str)

                    # Prevent building an infinitely large string in memory
                    if i > 2000:
                        formatted_output.append("... (truncated rows)")
                        break

            except Exception as e:
                logger.warning(f"Failed to parse frame values: {e}")

        if not formatted_output:
            return "Grafana Query returned successfully with NO data/rows found."

        final_text = "\\n".join(formatted_output)

        # Context window protection: limit to 15,000 characters
        if len(final_text) > 15000:
            final_text = (
                final_text[:15000] + "\\n... (TRUNCATED - reached 15,000 char limit)"
            )

        return final_text

    except requests.exceptions.RequestException as e:
        logger.error(f"Connection Failed for Grafana Query: {e}")
        return f"Connection Failed: {e}"
    except Exception as e:
        logger.error(f"Unknown error executing Grafana Query: {e}")
        return "Unexpected error."
