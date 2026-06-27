import requests
import configparser
import json
import logging
from datetime import datetime

# Logging setup
logging.basicConfig(filename="webex_integration.log",
                    level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

def load_config(path="config.ini"):
    config = configparser.ConfigParser()
    config.read(path)
    return config

def load_tokens(path="webex_tokens.json"):
    with open(path, "r") as f:
        return json.load(f)

def refresh_token(tokens, client_id, client_secret):
    response = requests.post("https://webexapis.com/v1/access_token", data={
        "grant_type": "refresh_token",
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": tokens["refresh_token"]
    })
    response.raise_for_status()
    new_tokens = response.json()
    with open("webex_tokens.json", "w") as f:
        json.dump(new_tokens, f, indent=2)
    logger.info("Webex token refreshed successfully.")
    return new_tokens

def send_message(token, room_id, text):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post("https://webexapis.com/v1/messages",
                             headers=headers,
                             json={"roomId": room_id, "text": text})
    response.raise_for_status()
    logger.info(f"Message sent to room {room_id}")

def send_file(token, room_id, file_path, text="File attached"):
    headers = {"Authorization": f"Bearer {token}"}
    with open(file_path, "rb") as f:
        response = requests.post(
            "https://webexapis.com/v1/messages",
            headers=headers,
            data={"roomId": room_id, "text": text},
            files={"files": f}
        )
    response.raise_for_status()
    logger.info(f"File {file_path} sent to room {room_id}")

def send_screenshot(token, room_id, screenshot_path, text="Screenshot attached"):
    send_file(token, room_id, screenshot_path, text)

def add_person(token, room_id, person_email):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post("https://webexapis.com/v1/memberships",
                             headers=headers,
                             json={"roomId": room_id, "personEmail": person_email})
    response.raise_for_status()
    logger.info(f"Added {person_email} to room {room_id}")

def delete_room(token, room_id):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(f"https://webexapis.com/v1/rooms/{room_id}",
                               headers=headers)
    response.raise_for_status()
    logger.info(f"Deleted room {room_id}")

def main():
    config = load_config()
    tokens = load_tokens()

    client_id = config["webex"]["client_id"]
    client_secret = config["webex"]["client_secret"]
    room_id = config["webex"]["room_id"]

    # Refresh token if expired
    if datetime.now() > datetime.fromisoformat(tokens["expires_at"]):
        tokens = refresh_token(tokens, client_id, client_secret)

    # Conditional actions based on config.ini
    if config["conditions"].getboolean("send_message"):
        send_message(tokens["access_token"], room_id, "🚨 Control-M Job Failed!")

    if config["conditions"].getboolean("send_screenshot"):
        screenshot_path = config["files"]["screenshot_path"]
        send_screenshot(tokens["access_token"], room_id, screenshot_path)

    if config["conditions"].getboolean("send_file"):
        file_path = config["files"]["file_path"]
        send_file(tokens["access_token"], room_id, file_path)

if __name__ == "__main__":
    main()
