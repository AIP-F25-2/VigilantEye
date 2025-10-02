import json, os
from .config import INDEX_PATH

def load_index():
    with open(INDEX_PATH, "r") as f: return json.load(f)

def save_index(idx):
    tmp = INDEX_PATH + ".tmp"
    with open(tmp, "w") as f: json.dump(idx, f, indent=2)
    os.replace(tmp, INDEX_PATH)
