from flask import Flask, request, jsonify
import requests
import os
from openai import OpenAI

app = Flask(__name__)

# ======================
# CONFIG
# ======================
VERIFY_TOKEN = "my_verify_token"

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

WHATSAPP_API_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ======================
# WEBHOOK VERIFICATION
# ======================
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Forbidden", 403

# ======================
# OPENAI AGENT
# ======================
def agent_reply(user_text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful WhatsApp assistant."},
            {"role": "user", "content": user_text}
        ]
    )
    return response.choices[0].message.content.strip()

# ======================
# SEND WHATSAPP MESSAGE
# ======================
def send_whatsapp(to, text):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }

    requests.post(WHATSAPP_API_URL, headers=headers, json=payload)

# ======================
# RECEIVE WHATSAPP MSG
# ======================
@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.json

    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        user_number = msg["from"]
        user_text = msg["text"]["body"]
    except Exception:
        return jsonify(status="ignored"), 200

    reply = agent_reply(user_text)
    send_whatsapp(user_number, reply)

    return jsonify(status="sent"), 200
