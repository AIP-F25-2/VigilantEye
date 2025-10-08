import os
from flask import Flask, request, jsonify
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# Force offline/local loading
LOCAL_DIR = os.environ.get("LOCAL_DIR", os.path.join(os.path.dirname(__file__), "models", "tinyllama"))
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")  # do not hit network

dtype = torch.float16 if torch.cuda.is_available() else torch.float32
device = "cuda" if torch.cuda.is_available() else "cpu"

tokenizer = AutoTokenizer.from_pretrained(LOCAL_DIR, use_fast=True)
model = AutoModelForCausalLM.from_pretrained(
    LOCAL_DIR,
    torch_dtype=dtype,
    low_cpu_mem_usage=True,
    trust_remote_code=True
).to(device)

app = Flask(__name__)

@app.route("/v1/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": LOCAL_DIR}), 200

SYSTEM_PROMPT = "You are a helpful assistant."
def build_chat(messages):
    sys = next((m["content"] for m in messages if m.get("role") == "system"), SYSTEM_PROMPT)
    convo = [f"<|system|>\n{sys}"]
    for m in messages:
        if m["role"] == "user":
            convo.append(f"<|user|>\n{m['content']}")
        elif m["role"] == "assistant":
            convo.append(f"<|assistant|>\n{m['content']}")
    convo.append("<|assistant|>\n")
    return "\n".join(convo)

@app.route("/v1/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    messages = data.get("messages") or [{"role": "user", "content": data.get("prompt", "")}]
    max_new_tokens = int(data.get("max_new_tokens", 256))
    temperature = float(data.get("temperature", 0.7))
    top_p = float(data.get("top_p", 0.9))

    prompt = build_chat(messages)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        ids = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=temperature > 0,
            temperature=temperature,
            top_p=top_p,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.eos_token_id,
        )
    text = tokenizer.decode(ids[0], skip_special_tokens=True)
    reply = text.split("<|assistant|>")[-1].strip()
    return jsonify({"reply": reply})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
