import os

import requests
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GRAPH_API_URL = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"


def send_message(phone, text):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": str(phone),
        "type": "text",
        "text": {"body": text},
    }
    response = requests.post(GRAPH_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def parse_incoming(data):
    """Extract sender phone and message text from Meta webhook payload.

    Returns (phone, message_text) or (None, None) if not a valid user message.
    """
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        # Ignore status updates (delivered, read, etc.)
        if "messages" not in value:
            return None, None

        message = value["messages"][0]
        phone = message["from"]
        text = message.get("text", {}).get("body", "")
        return phone, text.strip()
    except (KeyError, IndexError):
        return None, None
