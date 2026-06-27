import pyodbc
import pandas as pd
import configparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging

# Logging setup
logging.basicConfig(filename="query_mailer.log",
                    level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

def load_config(path="config.ini"):
    config = configparser.ConfigParser()
    config.read(path)
    return config

def run_query(config):
    conn_str = (
        f"DRIVER={{SQL Server}};"
        f"SERVER={config['database']['server']};"
        f"DATABASE={config['database']['name']};"
        f"UID={config['database']['user']};"
        f"PWD={config['database']['password']}"
    )
    conn = pyodbc.connect(conn_str)
    query = config['query']['sql']
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def transform(df, config):
    status_col = config['columns']['status']
    # Apply color coding
    def color_status(val):
        if val == "PASS":
            return "background-color: green; color: white;"
        elif val == "FAIL":
            return "background-color: red; color: white;"
        elif val == "ON HOLD":
            return "background-color: orange; color: black;"
        return ""
    styler = df.style.applymap(color_status, subset=[status_col])
    return styler.to_html()

def send_mail(config, html_table):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = config["mail"]["subject"]
    msg["From"] = config["mail"]["from"]
    msg["To"] = config["mail"]["to"]

    body = f"""
    <p>{config['mail']['body']}</p>
    {html_table}
    <p>{config['mail']['signature']}</p>
    """
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP(config["smtp"]["server"], int(config["smtp"]["port"])) as server:
        server.starttls()
        server.login(config["smtp"]["user"], config["smtp"]["password"])
        server.sendmail(msg["From"], [msg["To"]], msg.as_string())
    logger.info("Email sent successfully.")

def main():
    config = load_config()
    df = run_query(config)
    html_table = transform(df, config)
    send_mail(config, html_table)

if __name__ == "__main__":
    main()
