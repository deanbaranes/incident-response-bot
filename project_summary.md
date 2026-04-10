# סיכום מימוש: בוט לתגובה ראשונית לאירועים (Incident Response Bot)

המסמך הזה נועד להסביר בצורה פשוטה וברורה איך המערכת בנויה כעת, לאחר הריפקטורינג (Refactoring) שעשינו, שעבר ממבנה של קובץ יחיד (Monolithic) לארכיטקטורה מודולרית, מקצועית ומחולקת לשכבות.

## המבנה החדש של הפרויקט

המערכת מחולקת כעת למספר שכבות נפרדות, כדי לאפשר קוד נקי, תחזוקה קלה ובדיקתיות גבוהה (Production-Ready):
* **`api/`** - נקודות הקצה של השרת (Routes). כאן נמצא `webhook.py` שמאזין בממשק FastAPI.
* **`core/`** - הלוגיקה העסקית וניהול הזרימה (Flow). כאן נמצא `engine.py` ובו הפונקציה המרכזית `process_incident` שמריצה את הפעולות מהפלייבוק.
* **`services/`** - התמשקויות למערכות ושירותים חיצוניים (3rd Parties):
  * `github.py` - הורדת קבצי הגדרות / Playbooks מווסטים.
  * `grafana.py` - שאילתות למדדים חיים מול Prometheus פנימי וצילום דאשבורדים באמצעות דפדפן.
  * `ai.py` - עבודה מול מודל הבינה המלאכותית מבית גוגל (Gemini).
  * `email.py` - משלוח והכנת דוחות סיום דרך פרוטוקול SMTP.
* **`config.py`** - ריכוז של כל משתני הסביבה (Environment Variables) לחשיפה מרכזית מול קובץ `.env`.
* **`main.py`** - קובץ הריצה הראשי שמחבר את שכבת ה-API לשרת uvicorn.

---

בהתאם לשלבים שהוגדרו (Declarative Playbooks, Data Enrichment וכו'), כך זה מיושם בקוד החדש והמודולרי:

## 1. קריאת ההוראות מרחוק דרך גיטהאב (Declarative Playbooks)
**הדרישה:** משיכת קובץ YAML ללא קוד קשיח לפי שם ההתראה.
**המימוש החדש:**
נמצא תחת שירות עצמאי בקובץ `services/github.py`. הבוט לא יכול לגשת או להפריע למערכת ההפעלה, הדבר מופרד לחלוטין.
```python
def load_playbook(alert_name):
    """Download the relevant YAML playbook from GitHub."""
    file_name = alert_name.replace(' ', '_').lower()
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/playbooks/{file_name}.yaml"
    
    # חיבור ישיר מול ה-API של GitHub עם טוקן הרשאה להורדה
    response = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code == 200:
        # חילוץ קוד Base64 והעברתו ל-YAML Object
        content = base64.b64decode(response.json()['content']).decode('utf-8')
        return yaml.safe_load(content)
```

## 2. מוח מבוסס הגדרות וניהול אירוע אגנוסטי 
**הדרישה:** הבוט רץ על ה-YAML ומבצע פעולות לפי הסדר ללא התערבות.
**המימוש החדש:**
הניהול המרכזי שוכן כעת בקובץ בודד לניהול האירועים - `core/engine.py`. כל פעולה נקראת מתוך השירותים החיצוניים המתאימים לה.
```python
if playbook and "actions" in playbook:
    for action in playbook["actions"]:
        action_type = action.get("type")
        
        # --- צילום מסך ---
        if action_type == "capture_dashboard_screenshot":
            screenshot_path = capture_dashboard(target_url, unique_filename)
            
        # --- שאילת מדדים חיים ---
        elif action_type == "fetch_metrics":
            metric_val = fetch_grafana_metric(target, prom_query)
```

## 3. איסוף נתונים חיים מגרפאנה (Data Enrichment)
**הדרישה:** שאילתות בזמן אמת לגרפאנה לפי כוסיות משתלבות.
**המימוש החדש:**
הפך למודול בודד וממוקם ב- `services/grafana.py`. תומך באותנטיקציה מתקדמת מול הענן של גרפאנה.
```python
def fetch_grafana_metric(target_name, query):
    """Fetch live data from Grafana Cloud Prometheus API."""
    api_url = f"{base_url}/api/prom/api/v1/query"
    # שימוש ב-Basic Auth למול Instance ID + API Token
    response = requests.get(api_url, headers=headers, auth=auth, params={"query": query})
    if response.status_code == 200:
        result = response.json()
        value = result["data"]["result"][0]["value"][1]
        return f"{float(value):.1f}%"
```

## 4. צילום מסך אוטומטי לטובת חוקרים (RCA Accelerated)
**הדרישה:** אוטומציה לצילום עדויות ויזואליות שיוזרקו לדוח.
**המימוש החדש:**
אותו הקובץ: `services/grafana.py`. כעת המנגנון עוטף את ספריות ה-Playwright לפתיחת דפדפן ויראלי מסווג.
```python
def capture_dashboard(url, output_path="dashboard.png"):
    """Capture a screenshot of the Grafana dashboard."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # הפעלת קונטקסט עשיר ברזולוציית FullHD והמתנה מלאה לטעינת רשת
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()
        page.goto(url, wait_until="networkidle")
        time.sleep(10)
        page.screenshot(path=output_path)
```

## 5. שילוב בינה מלאכותית ודיווח דוא"ל חכם
**הדרישה:** ניתוח המשלב טקסט ותמונה (ראייה ממוחשבת/Vision) שליחת המייל באופן מיידי.
**המימוש החדש:**
הלוגיקה נותקה וחולקה טכנית לחלוטין לשניים:
* `services/ai.py` - מתכלל את קטעי הטקסט עם התצלום שהופק לשליחה מול Google Gemini.
* `services/email.py` - הקמת תקשורת מוצפנת מול שרת SMTP לבניית המייל (כולל הגרפיקה המצורפת).

המפגש עצמו מבוקר דרך ה-`core/engine.py` בשני שלבים נקיים:
```python
elif action_type == "ai_analysis":
    # מחולל תובנות באמצעות מודל AI תוך שימוש במדדים המועשרים והתמונה
    ai_output = get_ai_analysis(alert_name, enriched_data, screenshot_path)

elif action_type == "send_notification":
    # בניית והדפסת דוח מלא הכולל עדות ויזואלית וממצא חכם
    send_email_report(subject, report_body, attachment_path=screenshot_path)
```

## לסיכום הארכיטקטורה החדשה
הפרויקט עבר ממצב MVP למצב מוכן לייצור (Production). כל מודול (שירותים חיצוניים, לב המערכת והגדרות) מבודד.
המשמעות היא שניתן לחבר רכיב AI חדש, להחליף אלטרנטיבה לשרת דוא"ל (SSO / SendGrid) או לשנות את מודל ההרשאות לגרפאנה ישירות בשכבת ה-`services`, ללא שום חשש לשבירת הזרימה המורכבת של הלוגיקה העסקית. ארכיטקטורה זו נחשבת תקינת-תעשייה בעולמות ה-Python.
