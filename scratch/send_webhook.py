import requests

payload = {
    "alerts": [
        {
            "status": "firing",
            "labels": {"alertname": "high_cpu_usage"},
            "annotations": {
                "summary": "Test Alert: CPU usage is above 95% on instance prod-web-01 (This is a test to verify Slack)"
            },
        }
    ]
}

print("Sending test webhook to http://localhost:5000/webhook...")
try:
    res = requests.post("http://localhost:5000/webhook", json=payload, timeout=5)
    print("Response Status:", res.status_code)
    print("Response Body:", res.text)
except Exception as e:
    print("Failed to connect:", e)
