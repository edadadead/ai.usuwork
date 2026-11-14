import os
import time
import threading
import requests
from flask import Flask, send_from_directory

# Explicitly mapping mimetypes so the browser accepts the JS module
app = Flask(__name__, static_url_path='', static_folder='.')

@app.after_request
def add_header(response):
    # Ensure JavaScript modules are served with the correct MIME type
    if response.path.endswith('.js'):
        response.headers['Content-Type'] = 'application/javascript; charset=utf-8'
    return response

# --- KEEP-ALIVE WORKER ---
def self_ping_worker():
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not app_url:
        return
    while True:
        time.sleep(600)
        try:
            requests.get(f"{app_url}/health", timeout=5)
        except Exception:
            pass

threading.Thread(target=self_ping_worker, daemon=True).start()

@app.route("/", methods=["GET"])
def home():
    return send_from_directory('.', 'index.html')

@app.route("/admin", methods=["GET"])
def admin_panel():
    return send_from_directory('.', 'admin.html')

@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
