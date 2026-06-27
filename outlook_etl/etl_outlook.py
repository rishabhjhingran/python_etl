import os
import yaml
import logging
import pandas as pd
from datetime import datetime, timedelta
from exchangelib import Credentials, Account, DELEGATE, Message
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import time

# ---------------------------
# Logging setup
# ---------------------------
logging.basicConfig(
    filename="etl_outlook.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------
# Load configuration
# ---------------------------
def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

# ---------------------------
# Extract: Outlook mails from all folders
# ---------------------------
def extract_outlook(account, hours=9):
    cutoff = datetime.now() - timedelta(hours=hours)
    data = []

    # Traverse all folders and subfolders
    for folder in account.root.walk():
        try:
            items = folder.filter(datetime_received__gte=cutoff)
            for item in items:
                if isinstance(item, Message):
                    data.append({
                        "id": item.id,  # unique identifier
                        "subject": item.subject,
                        "sender": str(item.sender.email_address) if item.sender else None,
                        "received_time": item.datetime_received,
                        "body": item.text_body,
                        "is_read": item.is_read
                    })
        except Exception as e:
            logger.warning(f"Error reading folder {folder.name}: {e}")

    df = pd.DataFrame(data)
    logger.info(f"Extracted {len(df)} mails across all folders.")
    return df

# ---------------------------
# Transform: filter columns
# ---------------------------
def transform(df):
    df = df[["id", "subject", "sender", "received_time", "body", "is_read"]]
    logger.info("Transformation completed successfully.")
    return df

# ---------------------------
# Load: SQL Server with MERGE INTO
# ---------------------------
def load_to_db(df, db_uri, table="outlook_mails"):
    try:
        engine = create_engine(db_uri)
        with engine.begin() as conn:
            for _, row in df.iterrows():
                merge_sql = text(f"""
                MERGE {table} AS target
                USING (SELECT :id AS id, :subject AS subject, :sender AS sender,
                              :received_time AS received_time, :body AS body, :is_read AS is_read) AS source
                ON target.id = source.id
                WHEN MATCHED THEN
                    UPDATE SET subject = source.subject,
                               sender = source.sender,
                               received_time = source.received_time,
                               body = source.body,
                               is_read = source.is_read
                WHEN NOT MATCHED THEN
                    INSERT (id, subject, sender, received_time, body, is_read)
                    VALUES (source.id, source.subject, source.sender, source.received_time, source.body, source.is_read);
                """)
                conn.execute(merge_sql, row.to_dict())
        logger.info(f"MERGE completed for {len(df)} records.")
    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise

# ---------------------------
# Main ETL loop (runs every minute)
# ---------------------------
def main():
    config = load_config()
    creds = Credentials(config["outlook"]["email"], config["outlook"]["password"])
    account = Account(
        primary_smtp_address=config["outlook"]["shared_mailbox"],
        credentials=creds,
        autodiscover=True,
        access_type=DELEGATE
    )

    while True:
        try:
            df = extract_outlook(account, hours=9)
            df = transform(df)
            load_to_db(df, config["database"]["uri"])
            logger.info("ETL cycle completed successfully.")
        except Exception as e:
            logger.critical(f"ETL cycle failed: {e}")
        time.sleep(60)  # run every minute

if __name__ == "__main__":
    main()
