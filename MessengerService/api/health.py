import os
import psutil
import logging
from flask import Blueprint, jsonify

# Define Blueprint
bp = Blueprint("health", __name__, url_prefix="/health")

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Optional: add console handler so logs appear in terminal
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(console_handler)


@bp.route("/stats", methods=["GET"])
def home():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    cpu_percent = process.cpu_percent(interval=0.1)

    met = {
        "cpu_percent": cpu_percent,
        "memory_mb": round(mem_info.rss / 1024 ** 2, 2),  # round for readability
        "threads": process.num_threads()
    }

    logger.info(f"System stats: {met}")
    return jsonify(met)  # jsonify so Flask returns proper JSON


@bp.route("/test", methods=["GET"])
def test():
    logger.info("Test endpoint called")
    return "Success"
