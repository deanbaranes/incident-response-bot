import hmac
import hashlib
import requests
import json

EC2_IP = "13.60.245.177"
WEBHOOK_SECRET = "testing_secret_key_123"
URL = f"http://{EC2_IP}:5000/webhook"

payload = {
    "alerts": [
        {
            "status": "firing",
            "labels": {"alertname": "AWS-Deployment-Test", "severity": "critical"},
            "annotations": {
                "description": "Testing if the webhook works from the outside world!"
            },
        }
    ]
}

body = json.dumps(payload).encode("utf-8")
signature = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()

headers = {
    "Content-Type": "application/json",
    "X-Grafana-Webhook-Signature": f"sha256={signature}",
}

print(f"Sending webhook to {URL}...")
try:
    response = requests.post(URL, data=body, headers=headers, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
