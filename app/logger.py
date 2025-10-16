import logging
import sys
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("surveillance-pipeline")
logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

# Rotating file logger for production-like logs
file_handler = RotatingFileHandler("app.log", maxBytes=5_000_000, backupCount=3)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
