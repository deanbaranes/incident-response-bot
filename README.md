# Incident Response Bot

An open-source automated incident triage bot. When Grafana fires an alert, the bot immediately fetches live metrics, captures a dashboard screenshot, runs AI-powered root cause analysis, and emails a full incident report — so on-call engineers start with context, not a blank slate.

```
Grafana alert → webhook → fetch metrics + screenshot → Gemini AI RCA → email report
```

## Features

- **Playbook-as-code** — YAML files in GitHub drive what happens per alert (metrics to pull, dashboard to screenshot, who to notify)
- **Live metric enrichment** — queries Prometheus directly so the report reflects the moment of the alert, not stale averages
- **Visual context** — headless Playwright captures a Grafana dashboard screenshot and attaches it to the report
- **AI root cause analysis** — Google Gemini analyzes metrics + screenshot and outputs 3 actionable troubleshooting steps
- **Multi-recipient email** — comma-separated `EMAIL_RECIPIENTS` env var; no code changes needed
- **Webhook authentication** — HMAC-SHA256 signature verification (Grafana-native)
- **Fail-fast startup** — app refuses to start if required env vars are missing

## Quickstart

### 1. Clone and install

```bash
git clone https://github.com/your-org/incident-response-bot.git
cd incident-response-bot
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — see "Configuration" below
```

### 3. Run

```bash
python main.py
# Server starts on http://0.0.0.0:5000
```

### 4. Expose to Grafana

```bash
ngrok http 5000
# Use the https URL as the Grafana Contact Point webhook URL
```

### 5. Test the webhook

```bash
# Without a signature (WEBHOOK_SECRET not set):
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"alerts":[{"status":"firing","labels":{"alertname":"HighCPUUsage"},"annotations":{"summary":"CPU at 95%"}}]}'

# With signature verification enabled:
BODY='{"alerts":[{"status":"firing","labels":{"alertname":"HighCPUUsage"},"annotations":{"summary":"CPU at 95%"}}]}'
SIG=$(echo -n "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print "sha256="$2}')
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Grafana-Webhook-Signature: $SIG" \
  -d "$BODY"
```

## Docker

```bash
cp .env.example .env  # fill in values
docker-compose up
```

## Configuration

All configuration is via environment variables. Copy [`.env.example`](.env.example) to `.env` and fill in the values.

| Variable | Required | Default | Description |
|---|---|---|---|
| `WEBHOOK_SECRET` | No | — | HMAC-SHA256 secret shared with Grafana. Strongly recommended in production. |
| `GITHUB_TOKEN` | **Yes** | — | GitHub PAT with repo read access (playbook store) |
| `GITHUB_REPO` | **Yes** | — | `owner/repo` containing playbook YAML files |
| `GEMINI_API_KEY` | **Yes** | — | Google AI Studio API key |
| `EMAIL_SENDER` | **Yes** | — | Gmail address used to send reports |
| `EMAIL_PASSWORD` | **Yes** | — | Gmail app password |
| `EMAIL_HOST` | No | `smtp.gmail.com` | SMTP server hostname |
| `EMAIL_PORT` | No | `587` | SMTP port (STARTTLS) |
| `EMAIL_RECIPIENTS` | No | `EMAIL_SENDER` | Comma-separated recipient list |
| `GRAFANA_URL` | **Yes** | — | Base URL of your Grafana instance |
| `GRAFANA_USERNAME` | No | — | Grafana Cloud Prometheus instance ID (omit for bearer-auth) |
| `GRAFANA_TOKEN` | **Yes** | — | Service account token with Metrics Reader role |
| `GRAFANA_DASHBOARD_URL` | No | — | Fallback dashboard URL when playbook omits one |

## Playbooks

Playbooks are YAML files stored in your GitHub repo. The bot loads `{alertname}.yaml` (case-sensitive) when an alert fires.

```yaml
# playbooks/HighCPUUsage.yaml
name: High CPU Usage Response
instruction: >
  Focus on processes consuming the most CPU. Check for runaway jobs or
  recent deployments. Suggest scaling options if usage is sustained.
actions:
  - type: capture_dashboard_screenshot
    url: https://your-org.grafana.net/d/abc123/overview   # optional; falls back to GRAFANA_DASHBOARD_URL

  - type: fetch_metrics
    target: CPU Usage
    query: 100 - (avg(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)

  - type: fetch_metrics
    target: Memory Usage
    query: >
      100 * (1 - ((avg_over_time(node_memory_MemFree_bytes[5m]) +
      avg_over_time(node_memory_Cached_bytes[5m]) +
      avg_over_time(node_memory_Buffers_bytes[5m])) /
      avg_over_time(node_memory_MemTotal_bytes[5m])))

  - type: ai_analysis

  - type: send_notification
```

### Available action types

| Action | Description |
|---|---|
| `capture_dashboard_screenshot` | Takes a Playwright screenshot of a Grafana dashboard |
| `fetch_metrics` | Queries Prometheus and adds the result to AI context |
| `ai_analysis` | Sends accumulated context + screenshot to Gemini for RCA |
| `send_notification` | Emails the full incident report to `EMAIL_RECIPIENTS` |

### Fallback behaviour

If no playbook matches the alert name, the bot runs a text-only AI analysis and sends a plain email with a note to create a playbook.

## Architecture

```
api/
  webhook.py      ← FastAPI endpoint, HMAC auth, Pydantic validation
core/
  engine.py       ← Orchestrates playbook action sequence
services/
  grafana.py      ← Prometheus metric queries + Playwright screenshots
  ai.py           ← Google Gemini integration
  email.py        ← SMTP delivery
  github.py       ← Playbook retrieval from GitHub
playbooks/        ← Example YAML playbooks
config.py         ← Env var loading with fail-fast validation
main.py           ← FastAPI app entry point
```

## Grafana setup

1. Go to **Alerting → Contact Points → New contact point**
2. Type: **Webhook**
3. URL: your ngrok/public URL + `/webhook`
4. Optional: set **Webhook secret** — copy the same value to `WEBHOOK_SECRET` in your `.env`
5. Add the contact point to an **Alert rule** or **Notification policy**

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) (coming soon). PRs welcome — especially new playbook examples and additional notifier integrations (Slack, PagerDuty, Jira).

## Security

See [SECURITY.md](SECURITY.md) for the threat model and vulnerability reporting process.

## License

Apache 2.0 — see [LICENSE](LICENSE).
