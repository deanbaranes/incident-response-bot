import requests
import os
from dotenv import load_dotenv

load_dotenv()

GRAFANA_TOKEN = os.getenv("GRAFANA_TOKEN")


def list_datasources():
    url = "https://dinbaranes.grafana.net/api/datasources"
    headers = {"Authorization": f"Bearer {GRAFANA_TOKEN}"}
    print(f"Listing Datasources: {url}")
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            ds_list = response.json()
            for ds in ds_list:
                print(
                    f"ID: {ds['id']}, Name: {ds['name']}, Type: {ds['type']}, URL: {ds['url']}"
                )
        else:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    list_datasources()
