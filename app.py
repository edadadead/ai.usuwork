import os
import time
import threading
import requests
from flask import Flask, request, jsonify
from google import genai

app = Flask(__name__)

# Initialize the Google GenAI client using the environment variable GEMINI_API_KEY
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- AUTO-TRAIN / KEEP-ALIVE WORKER ---
# Render free tier spins down after 15 minutes of inactivity. 
# This background thread pings its own URL every 10 minutes to prevent sleep.
def self_ping_worker():
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not app_url:
        print("Render external URL not found. Self-ping disabled.")
        return

    print(f"Starting self-ping keep-alive loop for: {app_url}")
    while True:
        time.sleep(600)  # Wait for 10 minutes (600 seconds)
        try:
            response = requests.get(f"{app_url}/health")
            print(f"Self-ping status: {response.status_code}")
        except Exception as e:
            print(f"Self-ping failed: {e}")

# Start the background thread when the Flask app boots up
threading.Thread(target=self_ping_worker, daemon=True).start()


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "status": "online",
        "message": "Smart AI Render Server is running and awake!"
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_prompt = data.get("prompt", "")

    if not user_prompt:
        return jsonify({"error": "Prompt is required"}), 400

    try:
        # Generate smart AI response using Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user_prompt,
        )
        return jsonify({
            "response": response.text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
