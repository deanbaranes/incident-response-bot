# 🤖 Automated Incident Triage & Enrichment AI

The system serves as a first responder, instantly enriching alerts with critical context, eliminating the manual toil of logging into various systems and helping engineers focus on key data within the alert.

## Core Use Cases
* 🚀 **Accelerated Root Cause Analysis (RCA):** Executes predefined queries immediately upon an alert, including:
  * 📈 Querying Grafana for current CPU / Mem usage levels via Grafana Data Source API.
  * 📷 Automatically capturing Grafana dashboard screenshots.
  * 🧠 Using an AI model to analyze the retrieved data to provide first responder insights.
  * 📧 Outputting all collected data to a dedicated Email mailing list defined in the Playbook flow.

## ⚙️ Functional Requirements
**Event Ingestion:** The system provides a highly available HTTP webhook endpoint that receives and normalizes alert payloads from Grafana.
**Declarative Playbooks:** Engineers can define incident response logic using YAML-based playbooks mapped to specific alert labels. These files are manageable via standard GitHub, part of the code repo.

## ⚡ How It Works
1. **Alert Trigger:** Grafana Cloud detects an issue (e.g., High CPU) and sends a Webhook.
2. **Playbook Retrieval:** The bot fetches a specific YAML playbook from a private GitHub repository based on the alert name.
3. **Data Enrichment:** The bot connects to Grafana's Prometheus API via Basic Auth to pull real-time metrics, avoiding stale alert data.
4. **Visual Context:** The bot launches a headless browser (Playwright) to capture a live screenshot of the associated Grafana Public Dashboard.
5. **AI Analysis:** Google Gemini AI analyzes the alert context, live metrics, and provides 3 actionable troubleshooting steps.
6. **Reporting:** A professional incident report, complete with the attached dashboard screenshot and AI recommendations, is sent via email to the designated mailing list.

## 🛠️ Tech Stack
* **Language:** Python 3.x
* **Framework:** FastAPI (Asynchronous Webhook handling)
* **AI:** Google Generative AI (Gemini 2.5 Flash)
* **Monitoring:** Grafana Cloud (Prometheus & Public Dashboards)
* **Browser Automation:** Playwright (Chromium headless)
* **Infrastructure:** GitHub API (Playbook-as-Code)
* **Deployment:** Ngrok (Local Tunneling)


## 📂 Project Architecture
The project is built using a clean, layered architecture to ensure scalability and maintainability:

* `api/` - Routing layer. Listens for incoming Webhooks from Grafana/Alertmanager.
* `core/` - Business logic. The `engine.py` orchestrates the response by executing playbook actions sequentially.
* `services/` - Integration layer. Isolated modules for external APIs (`github.py`, `grafana.py`, `ai.py`, `email.py`).
* `playbooks/` - Declarative YAML files dictating what actions to take per alert.
* `config.py` - Centralizes environment variables, logging, and startup validation.
* `main.py` - Application entry point.

## 🚀 Setup & Installation
1. Clone the repository and install the dependencies (`playwright`, `fastapi`, `uvicorn`, `requests`, `pyyaml`, `google-generativeai`, `python-dotenv`, `pillow`).
2. Run `playwright install chromium` to install the required headless browser.
3. Create a `.env` file with the following keys:
   ```env
   # API Keys
   GEMINI_API_KEY=your_key
   
   # GitHub (Playbooks)
   GITHUB_TOKEN=your_token
   GITHUB_REPO=your_repo
   
   # Grafana Cloud (Prometheus & GUI)
   GRAFANA_URL=https://prometheus-prod...grafana.net
   GRAFANA_USERNAME=your_prometheus_instance_id
   GRAFANA_TOKEN=your_service_account_token_with_metrics_read
   GRAFANA_DASHBOARD_URL=https://your-org.grafana.net/public-dashboards/your_public_link
   
   # Email Config
   EMAIL_SENDER=your_gmail
   EMAIL_PASSWORD=your_app_password
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   ```
4. Start the server:
   ```bash
   python main.py
   ```
5. Expose with Ngrok:
   ```bash
   ngrok http 5000
   ```
