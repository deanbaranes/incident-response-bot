"""Send a signed test alert to a deployed bot.

Usage:
    WEBHOOK_URL=http://<host>:5000/webhook WEBHOOK_SECRET=<secret> \
        python scripts/test_aws_webhook.py
"""

import hashlib
import hmac
import json
import os
import sys

import requests

URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not URL or not WEBHOOK_SECRET:
    sys.exit("Set WEBHOOK_URL and WEBHOOK_SECRET environment variables first.")

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
