# Code Review & Refactoring Strategy: Incident Response Bot

## 1. Executive Summary (תקציר מנהלים)
הפרויקט `incident-response-bot` מציג ארכיטקטורה מודרנית וטובה מאוד, המבוססת על **FastAPI, Kafka ו-Design Patterns** חכמים (כמו Strategy Pattern לניהול פעולות Playbook). ההפרדה בין ה-API (Producer) לבין עיבוד הרקע (Consumer) היא פרקטיקה מצוינת ל-Production שמאפשרת עמידות וגדילה (Scalability).

עם זאת, נמצאו **באג קריטי שמונע מהבוט לבצע פעולות**, בעיות ביצועים סביב שימוש ב-I/O חוסם (Blocking) וכן חולשת אבטחה פוטנציאלית בטעינת קבצים (Path Traversal).

---

## 2. Critical Issues (Security & Bugs)

### 🔴 באג קריטי: Handlers Registration (קוד שלא ירוץ לעולם)
במערכת מיושם מנגנון `ActionRegistry` מעולה. הבעיה היא שהמחלקות של ה-Handlers (בתיקיית `core/actions/handlers`) **מעולם לא מיובאות (Imported) בשום מקום בקוד**.
בקובץ `core/engine.py` נכתבה ההערה `# Import handlers to trigger registration` אך בפועל יובאו מודולים אחרים.
**התוצאה:** בזמן אמת, ה-Registry תמיד יהיה ריק, כל הפעולות ב-Playbook יכשלו, והבוט תמיד ידפיס `Unknown action type in playbook`.

### 🔴 אבטחה: Path Traversal (LFI) בטעינת פלייבוקים
בקובץ `services/playbooks.py`:
```python
file_name = alert_name.replace(" ", "_").lower() + ".yaml"
path = os.path.join(PLAYBOOKS_DIR, file_name)
```
הפונקציה סומכת על שם ההתראה (שמגיע מ-Grafana, קלט חיצוני) ורק מחליפה רווחים. תוקף יכול לשלוח Alert בשם `../../../etc/passwd` או לנווט לתיקיות רגישות. חובה להשתמש ב-Regex קשוח או ב-`os.path.basename` לנטרול פריצות.

---

## 3. Architecture & Performance Flaws

### ⚠️ צווארי בקבוק ביצועיים (Blocking I/O באפליקציה אסינכרונית)
FastAPI ו-AIOKafka בנויים לרוץ בצורה אסינכרונית. עם זאת, שירותי הליבה כותבים קוד סינכרוני וחוסם, ומבוצע להם "מעקף" ע"י `asyncio.to_thread`:
1. `services/grafana.py`, `services/slack.py`, `services/jira.py` - כולם משתמשים ב-`requests` הסינכרוני, במקום ב-`httpx` (בו השתמשתם יפה בשירותי PagerDuty ו-OpsGenie).
2. `services/email.py` - משתמש ב-`smtplib` החוסם. כדאי לעבור ל-`aiosmtplib`.

### ⚠️ ביצועי Playwright כבדים במיוחד
בקובץ `services/grafana.py`, הפונקציה `capture_dashboard` מריצה דפדפן שלם מחדש:
```python
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
```
הקמת דפדפן Chromium לכל אירוע (Incident) צורכת המון CPU וזיכרון ולוקחת מספר שניות.
**המלצה:** יש להרים דפדפן אחד פתוח ברקע בעלייה (Lifecycle hook), ולהשתמש ב-`browser.new_context()` בלבד פר בקשה, וכמובן להשתמש ב-`playwright.async_api`.

---

## 4. Clean Code & Cleanup (DRY & YAGNI)

### 🧹 הפרת Single Responsibility (SRP)
בקובץ `core/actions/handlers/grafana.py`, מחלקת `FetchMetricsHandler` מכילה בתוכה שאילתות PromQL קשיחות (Hardcoded) עבור CPU ו-Memory:
```python
if "cpu" in target.lower():
    prom_query = "100 - (avg(rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)"
```
זהו Anti-Pattern. הקוד לא צריך להכיר לוגיקה תשתיתית של השרתים. אם השאילתה אינה מסופקת בפלייבוק, הפעולה אמורה להיכשל או לשלוף מתוך מילון קונפיגורציה חיצוני.

### 🧹 יישור קו טכנולוגי (Tech Stack Alignment)
יש ערבוב בין ספריות סינכרוניות ואסינכרוניות שעושות את אותו הדבר (למשל `requests` מול `httpx`). יש למחוק את `requests` מ-`requirements.txt` ולעבוד בלעדית עם `httpx`.

---

## 5. Actionable Refactoring Plan

1. **[מיידי] תיקון ה-Registry Bug:** להוסיף ייבוא מסודר של ה-handlers לקובץ `core/engine.py` או ל-`main.py`.
2. **[מיידי] אבטחה ב-playbooks.py:** תיקון ה-Path Traversal באמצעות וידוא שם קובץ תקין (אלפא-נומרי בלבד).
3. **[ארכיטקטורה] אסינכרוניות מלאה:** המרת `services/slack.py`, `services/jira.py`, `services/grafana.py` מ-`requests` ל-`httpx.AsyncClient`.
4. **[ארכיטקטורה] אסינכרוניות Email:** מעבר ל-`aiosmtplib`.
5. **[ביצועים] Playwright Caching:** שיכתוב המודול כדי שישתמש ב-`playwright.async_api` וינהל Browser Context אחד רב-פעמי.

---

## 6. Code Snippets (Refactored)

### Fix 1: Registry Auto-Import (`core/actions/__init__.py`)
כדי למנוע את הבאג בו Handlers לא נרשמים, יש לטעון אותם אוטומטית. בקובץ `core/engine.py` החלף את ההערה לייבוא הזה:

```python
# core/engine.py
from core.actions.registry import ActionRegistry

# 🟢 FIX: Import all handlers to trigger their ActionRegistry.register() logic
import core.actions.handlers.grafana
import core.actions.handlers.notifications
import core.actions.handlers.ticketing
```

### Fix 2: Secure Playbook Loading (`services/playbooks.py`)
```python
import os
import re
import yaml
import logging

logger = logging.getLogger(__name__)
PLAYBOOKS_DIR = os.getenv("PLAYBOOKS_DIR", os.path.join(os.path.dirname(__file__), "..", "playbooks"))

def load_playbook(alert_name: str) -> dict | None:
    # 🟢 FIX: Strict regex to prevent Directory Traversal (LFI)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', alert_name).lower()
    file_name = f"{safe_name}.yaml"
    path = os.path.join(PLAYBOOKS_DIR, file_name)

    # 🟢 FIX: Ensure the resolved path strictly resides within PLAYBOOKS_DIR
    if not os.path.abspath(path).startswith(os.path.abspath(PLAYBOOKS_DIR)):
        logger.error(f"Security: Attempted path traversal detected: {alert_name}")
        return None

    try:
        with open(path, "r") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        return None
```

### Fix 3: Async Slack Notification (`services/slack.py`)
```python
import logging
import httpx
from core.settings import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

# 🟢 FIX: Replaced blocking 'requests' with 'httpx' async client
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.RequestError),
    reraise=True,
)
async def send_slack_alert(message: str, title: str = "Incident Alert", screenshot_path: str | None = None) -> bool:
    if screenshot_path:
        message += f"\n\n📎 *Visual Evidence*: A screenshot was captured at: `{screenshot_path}`"

    if not settings.SLACK_WEBHOOK_URL:
        logger.info(f"MOCK SLACK ALERT: Title: {title} | Message: {message[:100]}...")
        return True

    payload = {"text": f"*{title}*\n{message}"}

    async with httpx.AsyncClient() as client:
        response = await client.post(settings.SLACK_WEBHOOK_URL, json=payload, timeout=10.0)
        response.raise_for_status()

    logger.info(f"Successfully sent Slack alert: {title}")
    return True
```
