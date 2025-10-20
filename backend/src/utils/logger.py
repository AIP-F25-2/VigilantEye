"""Logging configuration and utilities."""

import logging
import sys
from pathlib import Path

from src.config import get_settings


def setup_logging() -> None:
    """Configure application logging."""
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    log_file = Path(settings.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.log_level)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler
    file_handler = logging.FileHandler(settings.log_file)
    file_handler.setLevel(settings.log_level)
    file_handler.setFormatter(console_formatter)
    root_logger.addHandler(file_handler)
    
    # Suppress overly verbose loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str = __name__) -> logging.Logger:
    """Get logger instance."""
    return logging.getLogger(name)
