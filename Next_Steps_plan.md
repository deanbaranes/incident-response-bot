# Incident Response Bot — Review & Improvement Plan

## Context

This project is an automated incident triage bot that:
1. Receives Grafana/AlertManager webhook events
2. Loads a YAML playbook from GitHub matching the alert name
3. Collects evidence (Prometheus metrics + Playwright dashboard screenshot)
4. Sends the screenshot + context to Google Gemini AI for RCA
5. Emails a comprehensive report to the admin

The architecture is clean and extensible (API → Core Engine → Services → External). The gaps are around security, correctness, flexibility, and integrations.

---

## Issues Found (Quick Summary)

### Critical / Correctness
| ID | Location | Issue |
|----|----------|-------|
| C1 | `api/webhook.py` | No webhook authentication — anyone can POST and trigger processing |
| C2 | `services/grafana.py:38` | No bounds check on Prometheus result — `result[0]["value"][1]` crashes with `IndexError` on empty response |
| C3 | `services/grafana.py:55` | `page.goto()` has no timeout — can hang indefinitely |
| C4 | `core/engine.py` | `data["alerts"]` accessed without existence check — malformed payload causes 500 |

### Medium / Quality
| ID | Location | Issue |
|----|----------|-------|
| M1 | `services/grafana.py:56` | `time.sleep(10)` after `wait_until="networkidle"` — redundant, adds 10s latency |
| M2 | `core/engine.py` | Playbook `instruction` field read but never passed to AI call |
| M3 | `services/github.py:19` | `print()` leaks internal repo URL to stdout |
| M4 | All services | Bare `except Exception` hides bugs and catches `SystemExit`/`KeyboardInterrupt` |
| M5 | `services/email.py:18` | Recipient hardcoded to `EMAIL_SENDER` — no team mailing list |
| M6 | `config.py:26` | Missing env vars only warn; app starts and fails later at runtime |

### Low / Polish
| ID | Issue |
|----|-------|
| L1 | Duplicate import of `send_email_report` in engine |
| L2 | No `.env.example` file |
| L3 | Screenshot PNGs accumulate on disk, never cleaned up |
| L4 | Zero test coverage |
| L5 | No structured (JSON) logging for log aggregation |

---

## Recommended Changes (Prioritized)

### Phase 1 — Fix Correctness & Security (must-do)

1. **Webhook signature verification** (`api/webhook.py`) ❌ OPEN
   - Add HMAC-SHA256 signature check using `WEBHOOK_SECRET` env var
   - Return 401 if `X-Grafana-Webhook-Signature` header is missing/invalid
   - Grafana supports webhook secrets natively

2. **Webhook input validation** (`api/webhook.py`) ❌ OPEN
   - Validate payload with Pydantic models: `alerts` array must exist and be non-empty
   - Reject oversized payloads (add `Content-Length` limit)

3. **Prometheus bounds check** (`services/grafana.py`) ❌ OPEN
   - Guard `result["data"]["result"]` before indexing
   - Return `None` or a descriptive string if empty
   - Also: add Viewer-only Grafana Service Account + query time-range validation

4. **Playwright timeout** (`services/grafana.py`) ❌ OPEN
   - Add `timeout=30000` to `page.goto()` call
   - Remove the redundant `time.sleep(10)`

5. **Startup validation** (`config.py`) ❌ OPEN
   - Change warnings to `raise RuntimeError` on missing required vars so the app fails fast

6. **Pass playbook `instruction` to AI** (`core/engine.py` + `services/ai.py`) ❌ OPEN
   - Extract `instruction` field from playbook
   - Pass as additional `system_prompt` context to `get_ai_analysis()`
---

### Phase 2 — Flexible Notifications & More Playbooks

1. **Slack notification channel** (new: `services/slack.py`) ❌ OPEN
   - Add `send_slack_alert(webhook_url, message, screenshot_path)` using Slack's Incoming Webhooks
   - Add `SLACK_WEBHOOK_URL` env var
   - Adds a new playbook action type: `send_slack_notification`
2. **Structured JSON logging** (`main.py`) ❌ OPEN
    - Switch to `python-json-logger` library
    - Add `incident_id` (UUID per alert) propagated through all log calls

---

### Phase 3 — Integration-Readiness

11. **Grafana OnCall integration** (new: `services/grafana_oncall.py`) ❌ OPEN
    - `send_grafana_oncall_alert(title, message, alert_name)` via Grafana OnCall webhook integration URL
    - New playbook action: `send_grafana_oncall_alert`
    - Needs `GRAFANA_ONCALL_WEBHOOK_URL` env var (from OnCall → Integrations → Webhook)
    - Raises `RuntimeError` if URL not configured; propagates `requests` errors

12. **OpsGenie integration** (new: `services/opsgenie.py`) ❌ OPEN
    - `send_opsgenie_alert(title, message, alert_name, priority="P3")` via OpsGenie Alerts API v2
    - Endpoint: `POST https://api[.eu].opsgenie.com/v2/alerts`
    - Auth: `Authorization: GenieKey $OPSGENIE_API_KEY`
    - New playbook action: `send_opsgenie_alert`
    - Needs `OPSGENIE_API_KEY`; optional `OPSGENIE_REGION=us|eu` (default `us`)

13. **PagerDuty integration** (new: `services/pagerduty.py`) ❌ OPEN
    - `create_pagerduty_incident(title, message, alert_name, severity=None)` via PagerDuty Events API v2
    - Endpoint: `POST https://events.pagerduty.com/v2/enqueue`
    - New playbook action: `create_pagerduty_incident`
    - Needs `PAGERDUTY_ROUTING_KEY`; optional `PAGERDUTY_SEVERITY=critical|error|warning|info`

    **Playbook example using all three:**
    ```yaml
    actions:
      - type: send_grafana_oncall_alert
        title: "High CPU on {{ alert_name }}"
      - type: send_opsgenie_alert
        priority: P2
      - type: create_pagerduty_incident
        severity: critical
    ```

14. **Jira ticket creation** (new: `services/jira.py`) ❌ OPEN
    - `create_jira_ticket(summary, description, priority)` using Jira REST API
    - New playbook action: `create_jira_ticket`
    - Needs `JIRA_BASE_URL`, `JIRA_PROJECT_KEY`, `JIRA_USER`, `JIRA_API_TOKEN`
---

### Phase 4 — Testing

15. **Unit tests** (new: `tests/`)
    - `tests/test_engine.py` — mock all services, assert correct action dispatch
    - `tests/test_grafana.py` — mock `requests`, assert bounds handling
    - `tests/test_ai.py` — mock Gemini SDK, assert fallback on empty response
    - `tests/test_webhook.py` — test signature validation, malformed payload rejection

---

### Phase 5 — Webhook Queue via Kafka

**Goal:** decouple webhook receipt from incident processing. `/webhook` becomes thin producer (validate + enqueue + 202). Worker container consumes, runs `process_incident`. Survives restarts, absorbs burst load, enables replay + horizontal scale.

#### 5.1 Docker Compose — add Kafka broker alongside bot

Env additions (`.env` / `config.py`):
```
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_INCIDENT_TOPIC=incident.webhooks
KAFKA_CONSUMER_GROUP=incident-responder
KAFKA_DLQ_TOPIC=incident.webhooks.dlq
```
#### 5.2 Producer — `api/webhook.py`

Flow: verify HMAC → Pydantic validate → assign `incident_id` (UUID) → publish → return `202 {"incident_id": ...}`.

- Library: `confluent-kafka` (librdkafka, fastest, prod-grade) or `aiokafka` (asyncio native). Prefer `aiokafka` since FastAPI is async.
- Key: `labels.alertname` (preserves ordering per-alert across partitions).
- Value: raw webhook JSON + `{"incident_id", "received_at", "source_ip"}` metadata.
- Producer config: `acks=all`, `enable.idempotence=true`, `linger.ms=5`, `compression.type=zstd`.
- Init producer at FastAPI startup (`lifespan` context), close on shutdown.
- If publish fails (broker down): return 503 so Grafana retries. Do NOT fall back to in-process processing — breaks durability guarantee.

#### 5.3 Consumer — `workers/incident_consumer.py`

New module. Long-running process (separate container).

- `AIOKafkaConsumer(topic, group_id=KAFKA_CONSUMER_GROUP, enable_auto_commit=False, auto_offset_reset="earliest")`.
- Loop: `async for msg in consumer` → deserialize → `await process_incident(payload)` → `await consumer.commit()` on success.
- **Manual commit after success only** = at-least-once delivery. `process_incident` must be idempotent (see 5.5).
- On exception: log with `incident_id`, send to DLQ topic, commit original offset (avoid poison-message loops).
- Concurrency: single async task per partition (Kafka ordering guarantee). Scale by adding partitions + consumer replicas.
- Graceful shutdown on SIGTERM: stop polling, finish in-flight, commit, close.

#### 5.4 Refactor `core/engine.py`

- Make `process_incident` async

#### 5.5 Idempotency

At-least-once means duplicate deliveries possible (rebalance, crash after action, before commit). Mitigations:
- Dedup key = `incident_id`. Keep short-lived set (Redis or in-memory TTL 1h) of processed IDs; skip if seen.
- Acceptable for v1: duplicate email / duplicate screenshot. Document as known behavior. Full exactly-once later via transactional outbox if needed.

#### 5.6 DLQ + observability

- Topic `incident.webhooks.dlq` — failed messages with exception trace in headers.
- Metrics: consumer lag (`kafka-consumer-groups.sh --describe`), messages processed, DLQ rate. Expose via `/metrics` Prometheus endpoint (`prometheus-fastapi-instrumentator`).
- Log `incident_id` on every hop (producer publish, consumer receive, each action).

#### 5.7 Tests

- `tests/test_producer.py` — mock producer, assert publish on POST, assert 503 on broker error.
- `tests/test_consumer.py` — use `testcontainers-kafka` or in-memory fake; assert commit only after success, DLQ on failure.
- Integration: `docker-compose up` → POST webhook → assert email received + offset committed.

#### 5.8 Migration/rollout

- Feature flag `USE_KAFKA_QUEUE=true|false` in `config.py`. Producer checks flag — if false, call `process_incident` inline (current behavior). Lets ops roll back without rebuild.
- Deploy order: 1) broker, 2) worker, 3) producer flip.

#### 5.9 External Kafka + Scaling

**Running Kafka as separate entity**

### Phase 6 — Grafana Query Language Support in Playbooks

**Goal:** playbooks can declare Grafana datasource queries (PromQL, LogQL, SQL, InfluxQL, etc.) executed via Grafana's `/api/ds/query` proxy — not just Prometheus direct. Lets one playbook span metrics + logs + SQL without per-datasource clients.
New playbook action type: `grafana_query`

