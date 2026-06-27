# 🐍 Python ETL & Automation — Production Pipelines from TCS

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Pandas](https://img.shields.io/badge/Pandas-2.2-150458?style=flat&logo=pandas)](https://pandas.pydata.org)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=flat)](https://www.sqlalchemy.org)
[![REST APIs](https://img.shields.io/badge/REST_APIs-ServiceNow_%7C_Webex-0052CC?style=flat)](https://restfulapi.net)
[![SQL Server](https://img.shields.io/badge/SQL_Server-PyODBC-CC2927?style=flat&logo=microsoftsqlserver&logoColor=white)](https://www.microsoft.com/sql-server)

A collection of **4 production Python automation pipelines** built and deployed covering REST API ingestion, Outlook mailbox ETL, SQL-to-email reporting, and Webex alerting via OAuth2.

These are cleaned, config-driven versions of systems that processed **1,000+ incidents monthly**, served **200+ associates**, and cut manual effort by up to **40%** across 10+ business units.

---

## 📁 Repository Structure

```
python-etl-automation/
│
├── incident_etl/               # ServiceNow REST API → Pandas → Excel report
│   ├── incident_etl.py
│   ├── config.yaml
│   └── requirements.txt
│
├── webex_integration/          # OAuth2 token refresh → Webex API alerting
│   ├── webex_integration.py
│   ├── config.ini
│   ├── webex_tokens.json       # token store (gitignored in production)
│   └── requirements.txt
│
├── outlook_etl/                # Outlook shared mailbox → SQL Server MERGE INTO
│   ├── etl_outlook.py
│   ├── config.yaml
│   ├── requirements.txt
│   └── README.md
│
└── db_query_mailer/            # SQL Server query → color-coded HTML → SMTP email
    ├── query_mailer.py
    ├── config.ini
    └── requirements.txt
```

---

## 🔧 Projects at a Glance

| Project | Source | Destination | Key Tech |
|---|---|---|---|
| [incident_etl](#1-incident-etl) | ServiceNow REST API | Excel report | `requests` `pandas` `openpyxl` `PyYAML` |
| [webex_integration](#2-webex-integration) | Control-M job failure trigger | Webex space | `requests` `OAuth2` `configparser` |
| [outlook_etl](#3-outlook-etl) | Outlook shared mailbox | SQL Server | `exchangelib` `SQLAlchemy` `pyodbc` |
| [db_query_mailer](#4-db-query-mailer) | SQL Server query | SMTP email (HTML) | `pyodbc` `pandas` `smtplib` |

---

## 1. Incident ETL

**`incident_etl/incident_etl.py`**

Queries the **ServiceNow REST API** for incidents across multiple assignment groups, transforms the nested response using Pandas, parses acknowledgement metadata from work notes, and exports a formatted Excel compliance report.

### What it does
- Fetches incidents per group within a configurable date range via `requests.get()` with basic auth
- Concatenates multiple group DataFrames into a single merged dataset
- Filters to only configured assignment groups and selects required columns
- Parses `Initial_Acknowledgement_Made_By` and `Initial_Acknowledgement_Made_At` from `work_notes` field
- Cleans linked values (ServiceNow returns objects with display links) by extracting the text portion
- Exports to Excel using `openpyxl`

### Architecture
```
ServiceNow REST API
  └── /api/now/table/incident?assignment_group=X&opened_atBETWEEN=...
        │
        ▼
  pd.DataFrame per group → pd.concat → transform()
        │  filter groups, select columns
        │  parse work_notes → ack_by, ack_time
        │  clean linked fields → extract_text()
        ▼
  incident_report.xlsx
```

### Config (`config.yaml`)
```yaml
servicenow:
  url: "https://instance.service-now.com/api/now/table/incident"
  user: "api_user"
  password: "api_password"

groups:
  - "Network Support"
  - "Database Admin"
  - "Application Support"

columns:
  - number
  - short_description
  - opened_at
  - state
  - assignment_group
  - assigned_to
  - work_notes

dates:
  start: "2026-06-01"
  end: "2026-06-30"

output:
  excel_file: "incident_report.xlsx"
```

### Run
```bash
pip install -r incident_etl/requirements.txt
python incident_etl/incident_etl.py
```

---

## 2. Webex Integration

**`webex_integration/webex_integration.py`**

Integrates with the **Webex API via OAuth2** to send real-time failure alerts when Control-M jobs fail. Handles automatic token refresh, conditional message/file/screenshot delivery, and full logging — designed to be triggered by a Control-M event action.

### What it does
- Loads OAuth2 tokens from `webex_tokens.json` and checks expiry
- Automatically refreshes the access token using the refresh token + client credentials when expired, and persists the new token back to disk
- Sends text messages, file attachments, and screenshot captures to a configured Webex room
- Supports adding new members to the alert space programmatically
- All actions are config-driven via `config.ini` conditions flags — no code changes needed to switch on/off features

### Architecture
```
Control-M Job Failure
        │
        ▼
  webex_integration.py
        │
        ├── load_tokens() → check expires_at
        │     └── refresh_token() if expired → POST /v1/access_token → save new tokens
        │
        ├── send_message()    → POST /v1/messages  { roomId, text }
        ├── send_screenshot() → POST /v1/messages  { roomId, files }
        └── send_file()       → POST /v1/messages  { roomId, files }
```

### OAuth2 token refresh
```python
def refresh_token(tokens, client_id, client_secret):
    response = requests.post("https://webexapis.com/v1/access_token", data={
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": tokens["refresh_token"]
    })
    new_tokens = response.json()
    with open("webex_tokens.json", "w") as f:
        json.dump(new_tokens, f, indent=2)   # persist refreshed token
    return new_tokens
```

### Config (`config.ini`)
```ini
[webex]
client_id = your_client_id
client_secret = your_client_secret
room_id = your_room_id

[conditions]
send_message = true
send_screenshot = true
send_file = false

[files]
screenshot_path = ./screenshots/failure.png
file_path = ./reports/job_failure.txt
```

### Run
```bash
pip install -r webex_integration/requirements.txt
python webex_integration/webex_integration.py
```

---

## 3. Outlook ETL

**`outlook_etl/etl_outlook.py`**

A continuous ETL loop that extracts emails from an **Outlook shared mailbox** (all folders and subfolders), transforms them into a structured DataFrame, and loads them into SQL Server using `MERGE INTO` for idempotent upserts — running every 60 seconds.

### What it does
- Connects to a shared mailbox using `exchangelib` with delegate access
- Traverses **all folders and subfolders** recursively, filtering emails from the last 9 hours
- Extracts: `id`, `subject`, `sender`, `received_time`, `body`, `is_read`
- Tracks emails by unique `id` — subsequent runs update `is_read` status dynamically (unread → read)
- Loads to SQL Server via `SQLAlchemy` + `MERGE INTO` — insert new emails, update existing ones
- Runs on a `while True` loop with `time.sleep(60)` — designed as a persistent service

### Architecture
```
Outlook Shared Mailbox (Exchange)
        │  exchangelib DELEGATE access
        │  account.root.walk() → all folders/subfolders
        │  filter: datetime_received >= now - 9 hours
        ▼
  pd.DataFrame [id, subject, sender, received_time, body, is_read]
        │
        ▼
  SQL Server: MERGE INTO outlook_mails
        ON target.id = source.id
        WHEN MATCHED → UPDATE (handles read status changes)
        WHEN NOT MATCHED → INSERT
        │
        ▼
  time.sleep(60) → repeat
```

### MERGE INTO (idempotent upsert)
```python
merge_sql = text(f"""
    MERGE {table} AS target
    USING (SELECT :id, :subject, :sender, :received_time, :body, :is_read) AS source
    ON target.id = source.id
    WHEN MATCHED THEN
        UPDATE SET subject=source.subject, sender=source.sender,
                   received_time=source.received_time, body=source.body,
                   is_read=source.is_read
    WHEN NOT MATCHED THEN
        INSERT (id, subject, sender, received_time, body, is_read)
        VALUES (source.id, source.subject, source.sender,
                source.received_time, source.body, source.is_read);
""")
```

### SQL Server table schema
```sql
CREATE TABLE outlook_mails (
    id            NVARCHAR(255) PRIMARY KEY,
    subject       NVARCHAR(MAX),
    sender        NVARCHAR(255),
    received_time DATETIME,
    body          NVARCHAR(MAX),
    is_read       BIT
);
```

### Run
```bash
pip install -r outlook_etl/requirements.txt
# Configure config.yaml with your mailbox credentials and DB URI
python outlook_etl/etl_outlook.py
```

---

## 4. DB Query Mailer

**`db_query_mailer/query_mailer.py`**

Connects to **SQL Server**, runs a configurable query, applies **colour-coded status formatting** (PASS/FAIL/ON HOLD) using Pandas Styler, and sends the result as an HTML table via SMTP — fully config-driven, zero hardcoded values.

### What it does
- Connects to SQL Server via `pyodbc` using config-driven connection string
- Executes the SQL query defined in `config.ini` into a Pandas DataFrame
- Applies cell-level colour coding: green for PASS, red for FAIL, orange for ON HOLD using `df.style.applymap()`
- Converts the styled DataFrame to an HTML table with `styler.to_html()`
- Sends as a multipart HTML email via `smtplib` with STARTTLS

### Architecture
```
SQL Server
  └── pyodbc connection → pd.read_sql(query)
        │
        ▼
  DataFrame → df.style.applymap(color_status)
        │       green=PASS / red=FAIL / orange=ON HOLD
        ▼
  styler.to_html() → MIMEMultipart HTML email
        │
        ▼
  smtplib SMTP → STARTTLS → sendmail()
```

### Colour coding logic
```python
def color_status(val):
    if val == "PASS":
        return "background-color: green; color: white;"
    elif val == "FAIL":
        return "background-color: red; color: white;"
    elif val == "ON HOLD":
        return "background-color: orange; color: black;"
    return ""

styler = df.style.applymap(color_status, subset=[status_col])
html_table = styler.to_html()
```

### Config (`config.ini`)
```ini
[database]
server = your_server
name = your_database
user = db_user
password = db_password

[query]
sql = SELECT id, test_name, status FROM test_results

[columns]
status = status

[mail]
subject = Daily Test Results
body = Please find below the latest test results:
from = automation@company.com
to = manager@company.com

[smtp]
server = smtp.company.com
port = 587
```

### Run
```bash
pip install -r db_query_mailer/requirements.txt
python db_query_mailer/query_mailer.py
```

---

## 🔑 Key Technical Decisions

**Why `MERGE INTO` instead of INSERT + UPDATE separately in `outlook_etl`?**
`is_read` status changes between ETL runs — an email that was unread at 9am may be read by 10am. If we used separate INSERT and UPDATE statements, we'd need two queries and risk race conditions. `MERGE INTO` atomically handles both in a single statement, and because it's keyed on the unique Outlook `id`, it's fully idempotent — re-running the ETL never creates duplicates.

**Why config-driven design across all projects?**
In production at TCS, the same pipeline runs across multiple environments (dev, UAT, prod) and multiple teams with different groups, URLs, and credentials. Hardcoding any value means a code change for every deployment. All four projects here use `config.yaml` or `config.ini` so the same script runs everywhere with zero code changes.

**Why `exchangelib` over the Microsoft Graph API for Outlook ETL?**
`exchangelib` works directly with Exchange Web Services (EWS) which is available on-premise and on Office 365 — no Azure app registration required. For corporate shared mailboxes in a TCS environment, EWS delegate access is simpler to provision than OAuth2 app permissions through Azure AD.

**Why OAuth2 token refresh in Webex integration rather than a long-lived token?**
Webex access tokens expire every 14 days. A long-lived token approach would require manual rotation — which defeats the purpose of automation. The refresh token flow in `webex_integration.py` automatically refreshes and persists the new token to `webex_tokens.json`, making the integration maintenance-free once set up.

---

## 🔗 Related Projects

- [E-Commerce Orders Pipeline — Databricks Jobs](https://github.com/rishabhjhingran/ecommerce-orders-pipeline-databricks)
- [Structured Streaming Pipeline — Watermarking & Window Agg](https://github.com/rishabhjhingran/structured-streaming-databricks)
- [Delta Lake Concepts — Deep Dive](https://github.com/rishabhjhingran/delta-lake-concepts-databricks)

---

*Built by [Rishabh Jhingran](https://github.com/rishabhjhingran) · 7 Years @ TCS · Databricks Certified Data Engineer Professional*
