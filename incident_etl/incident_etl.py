import requests
import pandas as pd
import yaml
import logging
from datetime import datetime

# Logging setup
logging.basicConfig(filename="incident_etl.log",
                    level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

def load_config(path="config.yaml"):
    with open(path, "r") as f:
        return yaml.safe_load(f)

def fetch_group_incidents(api_url, user, password, group, start_date, end_date):
    params = {"assignment_group": group, "opened_atBETWEEN": f"{start_date}@{end_date}"}
    response = requests.get(api_url, auth=(user, password), params=params)
    response.raise_for_status()
    return response.json()["result"]

def transform(df, required_columns):
    # Mask to ensure only assignment groups provided
    df = df[df["assignment_group"].isin(required_columns["groups"])]

    # Select required columns
    df = df[required_columns["columns"]]

    # Extract Initial Acknowledgement from work_notes
    df["Initial_Acknowledgement_Made_By"] = df["work_notes"].apply(lambda notes: parse_ack_by(notes))
    df["Initial_Acknowledgement_Made_At"] = df["work_notes"].apply(lambda notes: parse_ack_time(notes))

    # Clean link values for assignment_group and assigned_to
    df["assignment_group"] = df["assignment_group"].apply(lambda val: extract_text(val))
    df["assigned_to"] = df["assigned_to"].apply(lambda val: extract_text(val))

    return df

def parse_ack_by(notes):
    # Example logic: parse oldest timestamp and user
    return "parsed_user"

def parse_ack_time(notes):
    return datetime.now()

def extract_text(val):
    # Example: strip link to get text
    return val.split("/")[-1] if val else None

def main():
    config = load_config()
    api_url = config["servicenow"]["url"]
    user = config["servicenow"]["user"]
    password = config["servicenow"]["password"]
    groups = config["groups"]
    start_date = config["dates"]["start"]
    end_date = config["dates"]["end"]

    all_dataframes = []
    for group in groups:
        data = fetch_group_incidents(api_url, user, password, group, start_date, end_date)
        df = pd.DataFrame(data)
        all_dataframes.append(df)

    merged_df = pd.concat(all_dataframes, ignore_index=True)
    transformed_df = transform(merged_df, config)

    transformed_df.to_excel(config["output"]["excel_file"], index=False)
    logger.info(f"ETL completed. Exported {len(transformed_df)} records.")

if __name__ == "__main__":
    main()
