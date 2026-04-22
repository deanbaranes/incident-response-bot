---
name: New integration proposal
about: Propose a new notifier, AI provider, metric source, or playbook store
labels: integration
---

## Integration type

- [ ] Notifier (Slack, PagerDuty, Jira, …)
- [ ] AI provider (OpenAI, Anthropic, Ollama, …)
- [ ] Metric source (Datadog, New Relic, …)
- [ ] Playbook store (S3, local filesystem, …)
- [ ] Other

## Service / tool name

## Why this integration is valuable

<!-- Who uses this? What workflow does it unlock? -->

## Proposed action type name (if notifier)

```yaml
- type: send_xxx_notification
```

## Required env vars

| Variable | Description |
|---|---|
| `XXX_TOKEN` | … |

## Are you willing to implement this?

- [ ] Yes, I'll open a PR
- [ ] No, I'd like someone else to pick it up
