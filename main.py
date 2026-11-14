import os
import time
import threading
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

app = Flask(__name__, static_url_path='', static_folder='.')

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- SAFE BRAIN MEMORY MANAGEMENT (RAM-Optimized) ---
BRAIN_FILE = "brain.json"
BRAIN_DATA = {}

def load_brain():
    global BRAIN_DATA
    try:
        if os.path.exists(BRAIN_FILE):
            with open(BRAIN_FILE, "r", encoding="utf-8") as f:
                BRAIN_DATA = json.load(f)
            concepts = BRAIN_DATA.get('vocabulary_and_concepts', [])
            if len(concepts) > 1000:
                BRAIN_DATA['vocabulary_and_concepts'] = concepts[-1000:]
            print(f"Loaded brain.json with {len(BRAIN_DATA.get('vocabulary_and_concepts', []))} concepts.")
        else:
            BRAIN_DATA = {
                "ai_identity": {"name": "RenderBrain AI", "purpose": "Autonomous self-learning server AI."},
                "core_rules": ["Be helpful, concise, and smart."],
                "vocabulary_and_concepts": ["Flask", "Render", "Python", "AI", "Server"]
            }
            save_brain()
    except Exception as e:
        print(f"Error loading brain.json: {e}")

def save_brain():
    try:
        with open(BRAIN_FILE, "w", encoding="utf-8") as f:
            json.dump(BRAIN_DATA, f, indent=4)
    except Exception as e:
        print(f"Error saving brain.json: {e}")

load_brain()

def get_system_prompt():
    concepts = BRAIN_DATA.get('vocabulary_and_concepts', [])
    recent_context = concepts[-200:] if len(concepts) > 200 else concepts
    return f"""
You are {BRAIN_DATA.get('ai_identity', {}).get('name', 'AI')}.
Purpose: {BRAIN_DATA.get('ai_identity', {}).get('purpose', '')}
Core Rules: {json.dumps(BRAIN_DATA.get('core_rules', []))}
Recent Memory Focus: {json.dumps(recent_context)}
"""

# --- KEEP-ALIVE WORKER ---
def self_ping_worker():
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not app_url:
        return
    while True:
        time.sleep(600)  # Every 10 minutes
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


@app.route("/admin/shutdown", methods=["POST"])
def admin_shutdown():
    print("Admin shutdown command triggered!")
    def kill_server():
        time.sleep(1)
        os._exit(0)
    
    threading.Thread(target=kill_server).start()
    return jsonify({"message": "Server process successfully terminated."}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "memory_size": len(BRAIN_DATA.get('vocabulary_and_concepts', []))}), 200


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_prompt = data.get("prompt", "")

    if not user_prompt:
        return jsonify({"error": "Prompt is required"}), 400

    max_retries = 3
    backoff_delay = 2

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=get_system_prompt(),
                    temperature=0.7,
                )
            )
            
            ai_reply = response.text

            # Safe auto-training update (capped at 1000 items to protect RAM)
            words = [w.strip(".,!?()[]{}\"'`") for w in (user_prompt + " " + ai_reply).split() if len(w) > 4]
            current_concepts = set(BRAIN_DATA.get('vocabulary_and_concepts', []))
            
            new_additions = 0
            for word in words:
                if word not in current_concepts and not word.startswith("http"):
                    current_concepts.add(word)
                    new_additions += 1

            if new_additions > 0:
                BRAIN_DATA['vocabulary_and_concepts'] = list(current_concepts)[-1000:]
                save_brain()

            return jsonify({
                "response": ai_reply,
                "brain_stats": f"Learned {new_additions} new concepts! Total memory: {len(BRAIN_DATA['vocabulary_and_concepts'])}"
            })

        except Exception as e:
            error_message = str(e)
            if ("503" in error_message or "UNAVAILABLE" in error_message) and attempt < max_retries - 1:
                time.sleep(backoff_delay)
                backoff_delay *= 2
                continue
            
            return jsonify({"error": error_message}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
