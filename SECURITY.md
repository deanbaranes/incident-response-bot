# Security Policy

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Report it privately through GitHub: open the repository's **Security** tab and click **Report a vulnerability**. Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

You will receive an acknowledgement within 48 hours and a status update within 7 days.

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest `main` | Yes |
| older tags | No — please upgrade |

## Threat Model

### Webhook authentication
Grafana signs webhook requests with an HMAC-SHA256 signature using a shared secret. Set `WEBHOOK_SECRET` in your environment and configure the same value in Grafana Contact Point settings. Without this, any host that can reach your webhook endpoint can trigger incident processing and incur AI/email costs.

### Outbound network scope
The bot makes outbound requests to:
- Your Grafana/Prometheus instance (metric queries)
- Grafana dashboard URLs (Playwright screenshots)
- Google Gemini API (AI analysis)
- Your SMTP server (email delivery)
- Any notification integrations you enable (Slack, Jira, PagerDuty, OpsGenie, Grafana OnCall)

Playbooks are loaded from the local `playbooks/` directory. Alert names are sanitized and the resolved path is checked to stay inside that directory, which prevents path traversal.

Dashboard URLs come from playbook YAML files or the `GRAFANA_DASHBOARD_URL` env var. To prevent SSRF, the Playwright browser only navigates to URLs whose hostname matches the configured `GRAFANA_URL`; any other host (including internal addresses such as the cloud metadata service) is blocked. Still, do not accept playbooks from untrusted sources.

### Prompt injection
Alert names, labels and annotations are user-controlled data that is passed to the LLM as context. Mitigations in `services/ai.py`:
- Trusted rules are sent as the model's `system_instruction`, separate from the prompt.
- Alert data is wrapped in `<untrusted_alert_data>` tags, and the model is instructed never to follow instructions found inside them.
- Any copy of the wrapper tag inside alert data is removed, so the data cannot close the wrapper early.
- Alert data is truncated to 4,000 characters.

These measures reduce the risk but do not eliminate it. AI output is only used as text in reports and is never executed. Avoid granting the bot write access to external systems until additional output validation is in place. See the README section "Prompt injection protection" for details.

### Playbook safety
Playbooks are declarative YAML — they specify named action types (`capture_dashboard_screenshot`, `fetch_metrics`, `ai_analysis`, `send_notification`). There is no `shell` or `exec` action type. Do not add one without careful review.

### Secret handling
- All credentials are loaded from environment variables via `.env` (never committed).
- `.gitignore` excludes `.env`, `*.png`, and `venv/`.
- Use short-lived tokens with minimum required permissions:
  - Grafana: service account with Metrics Reader role only
  - Gmail: app password (not account password)

### Rate limiting / alert deduplication
In Kafka mode, the worker records each processed `incident_id` in a local SQLite database, so a message redelivered by Kafka (for example after a worker crash) is not processed twice.

This does not deduplicate separate webhook requests: each request gets a new `incident_id`. A misfiring alert rule in Grafana can still trigger repeated AI calls and emails, incurring cost and noise. Configure Grafana's repeat interval and group_wait settings to prevent floods. Rate limiting of repeated alerts is planned for a future release.
