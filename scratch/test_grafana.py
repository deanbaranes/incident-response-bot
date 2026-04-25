import requests
import os
from dotenv import load_dotenv

load_dotenv()

GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")


def test_grafana_api():
    url = "https://dinbaranes.grafana.net/api/health"
    headers = {"Authorization": f"Bearer {GRAFANA_TOKEN}"}
    print(f"Testing Grafana Health API: {url}")
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    test_grafana_api()
