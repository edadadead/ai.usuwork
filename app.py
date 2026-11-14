import os
import time
import threading
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from google import genai
from google.genai import types

# Flask setup (serving static files from current directory)
app = Flask(__name__, static_url_path='', static_folder='.')

# Initialize Google GenAI client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- UNLIMITED AUTO-TRAIN / LOAD LOCAL BRAIN MEMORY ---
BRAIN_FILE = "brain.json"
BRAIN_DATA = {}

def load_brain():
    global BRAIN_DATA
    try:
        if os.path.exists(BRAIN_FILE):
            with open(BRAIN_FILE, "r", encoding="utf-8") as f:
                BRAIN_DATA = json.load(f)
            print(f"Loaded brain.json with {len(BRAIN_DATA.get('vocabulary_and_concepts', []))} concepts (Unlimited growth mode).")
        else:
            BRAIN_DATA = {
                "ai_identity": {"name": "RenderBrain AI", "purpose": "Autonomous self-learning server AI with infinite memory."},
                "core_rules": ["Be helpful, concise, and learn continuously without limits."],
                "vocabulary_and_concepts": ["Flask", "Render", "Python", "AI", "Server"]
            }
            save_brain()
    except Exception as e:
        print(f"Error loading brain.json: {e}")

def save_brain():
    try:
        with open(BRAIN_FILE, "w", encoding="utf-8") as f:
            json.dump(BRAIN_DATA, f, indent=4)
        print("Brain.json updated and infinitely expanded successfully!")
    except Exception as e:
        print(f"Error saving brain.json: {e}")

# Initial load on boot
load_brain()

# Build system prompt dynamically (passing the latest 500 concepts to the model prompt to keep token size healthy, while storing everything infinitely in brain.json)
def get_system_prompt():
    concepts = BRAIN_DATA.get('vocabulary_and_concepts', [])
    # We send the latest/most recent 500 concepts to Gemini's system instructions, 
    # but brain.json retains 100% of everything ever learned forever!
    recent_context = concepts[-500:] if len(concepts) > 500 else concepts
    return f"""
You are {BRAIN_DATA.get('ai_identity', {}).get('name', 'AI')}.
Purpose: {BRAIN_DATA.get('ai_identity', {}).get('purpose', '')}
Core Rules: {json.dumps(BRAIN_DATA.get('core_rules', []))}
Total Lifetime Memory Concepts Stored: {len(concepts)}
Recent Memory Focus: {json.dumps(recent_context)}
"""

# --- KEEP-ALIVE WORKER ---
def self_ping_worker():
    app_url = os.environ.get("RENDER_EXTERNAL_URL")
    if not app_url:
        print("Render external URL not found. Self-ping disabled.")
        return

    print(f"Starting self-ping keep-alive loop for: {app_url}")
    while True:
        time.sleep(600)  # Every 10 minutes
        try:
            response = requests.get(f"{app_url}/health")
            print(f"Self-ping status: {response.status_code}")
        except Exception as e:
            print(f"Self-ping failed: {e}")

threading.Thread(target=self_ping_worker, daemon=True).start()


@app.route("/", methods=["GET"])
def home():
    return send_from_directory('.', 'index.html')


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "total_brain_memory_size": len(BRAIN_DATA.get('vocabulary_and_concepts', []))}), 200


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

            # --- INFINITE AUTO-TRAIN LOGIC ---
            words = [w.strip(".,!?()[]{}\"'`") for w in (user_prompt + " " + ai_reply).split() if len(w) > 4]
            current_concepts = set(BRAIN_DATA.get('vocabulary_and_concepts', []))
            
            new_additions = 0
            for word in words:
                if word not in current_concepts and not word.startswith("http"):
                    current_concepts.add(word)
                    new_additions += 1

            if new_additions > 0:
                # No limit! Stores everything infinitely.
                BRAIN_DATA['vocabulary_and_concepts'] = list(current_concepts)
                save_brain()

            return jsonify({
                "response": ai_reply,
                "brain_stats": f"Learned {new_additions} new concepts! Total lifetime memory size: {len(BRAIN_DATA['vocabulary_and_concepts'])}"
            })

        except Exception as e:
            error_message = str(e)
            if ("503" in error_message or "UNAVAILABLE" in error_message) and attempt < max_retries - 1:
                print(f"Model busy (503), retrying in {backoff_delay}s...")
                time.sleep(backoff_delay)
                backoff_delay *= 2
                continue
            
            return jsonify({"error": error_message}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
