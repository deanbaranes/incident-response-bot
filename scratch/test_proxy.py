import requests
import os
from dotenv import load_dotenv

load_dotenv()

GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")


def test_proxy_query():
    # ID 8 was the Prometheus datasource
    url = "https://dinbaranes.grafana.net/api/datasources/proxy/8/api/v1/query"
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
