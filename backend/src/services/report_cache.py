"""Helper module for report cache invalidation to avoid circular imports."""

import logging
from typing import Optional

import redis

from src.config.settings import get_config

logger = logging.getLogger(__name__)


def invalidate_report_cache(ticket_id: str, config=None) -> None:
    """
    Invalidate report cache for a ticket by deleting Redis keys.
    
    This is a standalone function to avoid circular imports between
    TicketService and ReportService.
    
    Args:
        ticket_id: The ticket ID to invalidate cache for
        config: Optional config object (uses get_config() if not provided)
    """
    if not ticket_id:
        return
    
    config = config or get_config()
    
    try:
        redis_client = redis.from_url(
            config.REDIS_URL,
            decode_responses=False,  # Binary data for PDF/JSON
        )
    except redis.RedisError as exc:
        logger.warning("Redis connection failed for cache invalidation: %s", exc)
        return
    
    try:
        cache_keys = [
            f"report:{ticket_id}:pdf",
            f"report:{ticket_id}:json",
        ]
        for key in cache_keys:
            redis_client.delete(key)
        logger.info(
            "Report cache invalidated",
            extra={"context": {"ticket_id": ticket_id}},
        )
    except Exception as exc:
        logger.warning(
            "Failed to invalidate report cache",
            extra={"context": {"ticket_id": ticket_id, "error": str(exc)}},
        )

