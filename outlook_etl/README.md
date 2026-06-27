📧 Outlook Shared Mailbox ETL (Python + SQL Server)
📌 Overview
This project implements a production-ready ETL pipeline that continuously extracts emails from a shared Outlook mailbox, transforms them into structured data, and loads them into a SQL Server database.

Key features:

Extract emails from all folders and subfolders in a shared mailbox using exchangelib.
Runs every minute, scanning the last 9 hours of mail activity.
Tracks emails by unique ID to avoid duplicates.
Transforms data into a clean DataFrame with:
Subject
Sender
Received Time
Body
Read/Unread status
Updates status dynamically (e.g., unread → read) in subsequent runs.
Loads data into SQL Server using MERGE INTO for upserts (insert new, update existing).
Full logging and error handling for auditability.
⚙️ Features
Config-driven (config.yaml) — no hardcoded secrets.
Logging with timestamps and severity levels (etl_outlook.log).
SQL Server integration via SQLAlchemy + PyODBC.
Continuous execution loop (time.sleep(60)).
MERGE INTO ensures idempotent updates.
🛠️ Tech Stack
Python 3.x
exchangelib (Outlook integration)
pandas (DataFrame transformations)
SQLAlchemy + PyODBC (Database connectivity)
YAML (Configuration management)
Logging (Audit trail)
📂 Project Structure
outlook-etl/ ├── etl_outlook.py # Main ETL script ├── config.yaml.example # Sample config (no secrets) ├── requirements.txt # Python dependencies ├── permissible_senders.log.example # (Optional legacy sender filter) └── README.md # Project documentation

🔧 Setup Instructions
1. Clone the repository
git clone https://github.com/rishabhjhingran/outlook-etl.git cd outlook-etl

2. Install the dependencies
pip install -r requirements.txt

3. Configure config.yaml
Create a config.yaml file (use .example as reference):

yaml outlook: email: "service_account@domain.com" password: "your_password" shared_mailbox: "shared_mailbox@domain.com"

database: uri: "mssql+pyodbc://username:password@dsn_name"

4. Run the ETL pipeline
bash python etl_outlook.py The script will:

Run every minute.

Extract mails from all folders/subfolders.

Update SQL Server with MERGE INTO.

📝 Logging Logs are written to etl_outlook.log.

Includes info, error, and critical messages for full auditability.

🗄️ SQL Server Table Schema Example schema for outlook_mails:

sql CREATE TABLE outlook_mails ( id NVARCHAR(255) PRIMARY KEY, subject NVARCHAR(MAX), sender NVARCHAR(255), received_time DATETIME, body NVARCHAR(MAX), is_read BIT ); 🚀 Future Enhancements Dockerize for containerized deployment.

Add CI/CD pipeline for automated testing.

Extend to support multiple shared mailboxes.

Add monitoring dashboards for ETL status.