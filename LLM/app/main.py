# main.py
import os
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, List

from app.schemas import ChatRequest, Message
from app.backends import HFClientBackend, LocalTransformersBackend, ChatBackend

app = FastAPI(title="Grok-style Chat Server")

# In-memory session store
SESSIONS: Dict[str, List[Dict[str, str]]] = {}

def get_backend() -> ChatBackend:
    backend = os.getenv("BACKEND", "local")
    if backend == "hf":
        # Defaults; override via env
        model = os.getenv("MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
        base_url = os.getenv("HF_BASE_URL")  # e.g., your self-hosted TGI/vLLM, or provider endpoint
        api_key = os.getenv("HF_API_KEY")
        return HFClientBackend(model=model, base_url=base_url, api_key=api_key)
    else:
        model = os.getenv("MODEL", "gpt2")
        return LocalTransformersBackend(model)

def get_history(session_id: str) -> List[Dict[str,str]]:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = []
    return SESSIONS[session_id]

@app.post("/chat")
def chat(req: ChatRequest, backend: ChatBackend = Depends(get_backend)):
    session_id = req.session_id or "default"
    history = get_history(session_id)
    # Append incoming messages to history
    history.extend([m.model_dump() for m in req.messages])

    def event_stream():
        for chunk in backend.generate(history, req.max_tokens, req.temperature, stream=True):
            yield f"data: {chunk}\n\n"
        # Append assistant message to history at the end (collect chunks)
    if req.stream:
        return StreamingResponse(event_stream(), media_type="text/event-stream")
    else:
        chunks = []
        for ch in backend.generate(history, req.max_tokens, req.temperature, stream=False):
            chunks.append(ch)
        text = "".join(chunks)
        history.append({"role": "assistant", "content": text})
        return JSONResponse({"role": "assistant", "content": text})
