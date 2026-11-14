import os
import time
import threading
import requests
from flask import Flask, request, jsonify, send_from_directory
from google import genai

# Tell Flask that index.html lives in the current working directory
app = Flask(__name__, static_url_path='', static_folder='.')

# Initialize the Google GenAI client using the environment variable GEMINI_API_KEY
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- AUTO-TRAIN / KEEP-ALIVE WORKER ---
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
    return send_from_directory('.', 'index.html')


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_prompt = data.get("prompt", "")

    if not user_prompt:
        return jsonify({"error": "Prompt is required"}), 400

    max_retries = 3
    backoff_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=user_prompt,
            )
            return jsonify({
                "response": response.text
            })
        except Exception as e:
            error_message = str(e)
            # If it's a 503 / overloaded error and we have retries left, wait and try again
            if ("503" in error_message or "UNAVAILABLE" in error_message) and attempt < max_retries - 1:
                print(f"Model busy (503), retrying in {backoff_delay}s (Attempt {attempt + 1}/{max_retries})...")
                time.sleep(backoff_delay)
                backoff_delay *= 2  # Double the wait time for the next retry
                continue
            
            # If it failed all retries or is a different error, return it
            return jsonify({"error": error_message}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
