import os
import time
import threading
import requests
from flask import Flask, send_from_directory

app = Flask(__name__, static_url_path='', static_folder='.')

# --- KEEP-ALIVE WORKER ---
def self_ping_worker():
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not app_url:
        print("Render external URL not found. Self-ping disabled.")
        return

    print(f"Starting self-ping keep-alive loop for: {app_url}")
    while True:
        time.sleep(600)  # Pings every 10 minutes to prevent sleep
        try:
            response = requests.get(f"{app_url}/health", timeout=5)
            print(f"Self-ping status: {response.status_code}")
        except Exception as e:
            print(f"Self-ping failed: {e}")

# Start background keep-alive thread
threading.Thread(target=self_ping_worker, daemon=True).start()


@app.route("/", methods=["GET"])
def home():
    # Serves your WebGPU local AI chat interface
    return send_from_directory('.', 'index.html')


@app.route("/admin", methods=["GET"])
def admin_panel():
    # Serves your admin dashboard
    return send_from_directory('.', 'admin.html')


@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
