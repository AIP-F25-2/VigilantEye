"""
Database utilities for VIGILANTEye
Centralized database operations to eliminate code duplication
"""

from app import db
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


def save_model(model_instance: Any) -> tuple[bool, Optional[str]]:
    """
    Save a model instance to database.
    
    Args:
        model_instance: SQLAlchemy model instance
        
    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        db.session.add(model_instance)
        db.session.commit()
        return True, None
    except Exception as e:
        logger.error(f"Database save error: {e}", exc_info=True)
        db.session.rollback()
        return False, str(e)


def save_models(model_instances: list) -> tuple[int, list[str]]:
    """
    Save multiple model instances to database.
    
    Args:
        model_instances: List of SQLAlchemy model instances
        
    Returns:
        Tuple of (saved_count: int, errors: list[str])
    """
    saved_count = 0
    errors = []
    
    for instance in model_instances:
        success, error = save_model(instance)
        if success:
            saved_count += 1
        else:
            errors.append(error)
    
    return saved_count, errors


def safe_db_operation(operation, *args, **kwargs):
    """
    Safely execute a database operation with rollback on error.
    
    Args:
        operation: Function to execute
        *args: Positional arguments for operation
        **kwargs: Keyword arguments for operation
        
    Returns:
        Tuple of (result, error_message)
    """
    try:
        result = operation(*args, **kwargs)
        db.session.commit()
        return result, None
    except Exception as e:
        logger.error(f"Database operation error: {e}", exc_info=True)
        db.session.rollback()
        return None, str(e)

