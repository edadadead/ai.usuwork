@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_prompt = data.get("prompt", "")
    history = data.get("history", []) # Receive past messages from frontend

    if not user_prompt:
        return jsonify({"error": "Prompt is required"}), 400

    if not GROQ_API_KEY:
        return jsonify({"error": "GROQ_API_KEY is not set in environment variables."}), 500

    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Build messages payload: System prompt + past conversation history + new user prompt
        messages = [{"role": "system", "content": get_system_prompt()}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": messages,
            "temperature": 0.7
        }

        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        res_data = resp.json()

        if resp.status_code != 200:
            return jsonify({"error": res_data.get("error", {}).get("message", "Groq API error")}), resp.status_code

        ai_reply = res_data["choices"][0]["message"]["content"]

        # Auto-training: Extract new concepts and save to brain.json
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
        return jsonify({"error": str(e)}), 500
