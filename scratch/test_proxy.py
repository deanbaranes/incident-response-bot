import requests
import os
from dotenv import load_dotenv

load_dotenv()

GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")
GRAFANA_PROMETHEUS_DATASOURCE_ID = os.getenv("GRAFANA_PROMETHEUS_DATASOURCE_ID", "8")


def test_proxy_query():
    # Use the dynamic Prometheus datasource ID
    url = f"https://dinbaranes.grafana.net/api/datasources/proxy/{GRAFANA_PROMETHEUS_DATASOURCE_ID}/api/v1/query"
    headers = {"Authorization": f"Bearer {GRAFANA_TOKEN}"}
    params = {"query": "up"}
    print(f"Testing Proxy Query: {url}")
    try:
        response = requests.get(url, headers=headers, params=params)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_proxy_query()
