# Contributing to Incident Response Bot

Thank you for your interest in contributing. This guide covers everything you need to get a working dev environment, run tests, and open a pull request.

## Table of contents

- [Development setup](#development-setup)
- [Running the bot locally](#running-the-bot-locally)
- [Code style](#code-style)
- [Running tests](#running-tests)
- [Opening a pull request](#opening-a-pull-request)
- [Adding a new integration](#adding-a-new-integration)
- [Adding a new playbook](#adding-a-new-playbook)

---

## Development setup

**Requirements:** Python 3.11+, Git.

```bash
git clone https://github.com/your-org/incident-response-bot.git
cd incident-response-bot

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install runtime + dev dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install the Playwright browser
playwright install chromium

# Install pre-commit hooks
pre-commit install
```

Copy the example env file and fill in at least the required values (see README for details):

```bash
cp .env.example .env
```

---

## Running the bot locally

```bash
python main.py
# Server starts on http://0.0.0.0:5000
```

Send a test webhook:

```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{"alerts":[{"status":"firing","labels":{"alertname":"HighCPUUsage"},"annotations":{"summary":"CPU at 95%"}}]}'
```

---

## Code style

This project uses:

| Tool | Purpose |
|---|---|
| [ruff](https://docs.astral.sh/ruff/) | Linting + import sorting |
| [black](https://black.readthedocs.io/) | Formatting |
| [mypy](https://mypy.readthedocs.io/) | Static type checking |

All checks run automatically on `git commit` via pre-commit. To run manually:

```bash
ruff check .
black --check .
mypy .
```

To auto-fix lint and formatting issues:

```bash
ruff check --fix .
black .
```

---

## Running tests

```bash
pytest tests/ -v
```

Tests live in `tests/`. Each service module has a corresponding test file (e.g., `tests/test_grafana.py`). External calls (Prometheus, Gemini, GitHub, SMTP) are mocked — no real credentials are needed to run the test suite.

---

## Opening a pull request

1. Fork the repo and create a feature branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Make your changes. Keep commits focused — one logical change per commit.
3. Ensure all checks pass:
   ```bash
   pre-commit run --all-files
   pytest tests/ -v
   ```
4. Push and open a PR against `main`. Fill in the PR template.
5. A maintainer will review within a few days.

**PR checklist (also in the PR template):**
- [ ] Pre-commit hooks pass
- [ ] Tests added or updated for new behaviour
- [ ] `.env.example` updated if new env vars introduced
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`
- [ ] README / docs updated if user-facing behaviour changed

---

## Adding a new integration

Integrations live in `services/`. Each module is a standalone file with one clear responsibility.

Steps to add, e.g., a Slack notifier:

1. Create `services/slack.py` with a `send_slack_alert(message, screenshot_path=None)` function.
2. Add any required env vars to `config.py` and `.env.example`.
3. Register a new action type in `core/engine.py` (add an `elif action_type == "send_slack_notification":` branch).
4. Add an example playbook in `playbooks/` that uses the new action.
5. Write tests in `tests/test_slack.py` (mock the Slack API call).
6. Document the new env vars in the README configuration table.

---

## Adding a new playbook

Playbooks are YAML files in `playbooks/` named exactly after the Grafana alert name (case-sensitive).

See the [playbook schema](README.md#playbooks) in the README and the existing examples in `playbooks/` for reference. Good playbook contributions include:

- A clear `name` and a helpful `instruction` that guides the AI analysis.
- At least one `fetch_metrics` action with a correct PromQL query.
- A comment explaining when the alert fires and what the expected impact is.
