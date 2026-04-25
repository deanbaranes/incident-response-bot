import requests
import os
from dotenv import load_dotenv

load_dotenv()

GRAFANA_URL = os.getenv("GRAFANA_URL")
GRAFANA_USERNAME = os.getenv("GRAFANA_USERNAME")
GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")


def test_query_basic():
    if not GRAFANA_URL:
        print("GRAFANA_URL not set")
        return

    base_url = GRAFANA_URL.rstrip("/")
    api_url = f"{base_url}/api/prom/api/v1/query"

    headers = {"Content-Type": "application/json"}
    auth = (GRAFANA_USERNAME, GRAFANA_TOKEN) if GRAFANA_USERNAME else None

    print(f"Testing Basic Auth at: {api_url}")
    try:
        response = requests.get(
            api_url, headers=headers, auth=auth, params={"query": "up"}, timeout=10
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")


def test_query_bearer():
    # Try the main Grafana instance URL
    grafana_instance_url = "https://dinbaranes.grafana.net"
    api_url = f"{grafana_instance_url}/api/prom/api/v1/query"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GRAFANA_TOKEN}",
    }

    print(f"\nTesting Bearer Auth at: {api_url}")
    try:
        response = requests.get(
            api_url, headers=headers, params={"query": "up"}, timeout=10
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")


def test_query_proxy():
    # We use the Grafana UI URL here because that's where the proxy lives
    grafana_ui_url = "https://dinbaranes.grafana.net"
    api_url = f"{grafana_ui_url}/api/datasources/proxy/8/api/v1/query"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GRAFANA_TOKEN}",
    }

    print(f"\nTesting Proxy Auth (DS 8) at: {api_url}")
    try:
        response = requests.get(
            api_url, headers=headers, params={"query": "up"}, timeout=10
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_query_basic()
    test_query_bearer()
    test_query_proxy()
