# Security Policy

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for security vulnerabilities.

Email **security@your-org.example.com** with:
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
- GitHub API (playbook retrieval)

Dashboard URLs come from playbook YAML files or the `GRAFANA_DASHBOARD_URL` env var. Do not accept playbooks from untrusted sources — a malicious playbook could point the Playwright browser at internal network addresses (SSRF). An allow-list guard is planned for a future release.

### Prompt injection
Alert labels and annotations are user-controlled data that is passed to the LLM as context. The bot wraps this data with clear role delimiters so the model treats it as data, not as instructions. Avoid granting the bot write access to external systems until additional output validation is in place.

### Playbook safety
Playbooks are declarative YAML — they specify named action types (`capture_dashboard_screenshot`, `fetch_metrics`, `ai_analysis`, `send_notification`). There is no `shell` or `exec` action type. Do not add one without careful review.

### Secret handling
- All credentials are loaded from environment variables via `.env` (never committed).
- `.gitignore` excludes `.env`, `*.png`, and `venv/`.
- Use short-lived tokens with minimum required permissions:
  - GitHub: read-only, scoped to the playbook repository
  - Grafana: service account with Metrics Reader role only
  - Gmail: app password (not account password)

### Rate limiting / alert deduplication
The bot processes every webhook request independently. A misfiring alert rule in Grafana can trigger repeated AI calls and emails, incurring cost and noise. Configure Grafana's repeat interval and group_wait settings to prevent floods. A built-in deduplication layer is planned for a future release.
