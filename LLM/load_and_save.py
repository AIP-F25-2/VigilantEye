import os
from transformers import snapshot_download

MODEL_ID = os.environ.get("MODEL_ID", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")
SAVE_DIR = os.environ.get("SAVE_DIR", os.path.join(os.path.dirname(__file__), "models", "tinyllama"))

os.makedirs(SAVE_DIR, exist_ok=True)
# Download the entire repo (config, tokenizer, safetensors) into SAVE_DIR
repo_path = snapshot_download(
    repo_id=MODEL_ID,
    local_dir=SAVE_DIR,
    local_dir_use_symlinks=False
)
print(f"Saved to: {repo_path}")
