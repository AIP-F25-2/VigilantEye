"""
Response utilities for VIGILANTEye
Centralized response formatting to eliminate code duplication
"""

from flask import jsonify
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# HTTP Status Codes
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_BAD_REQUEST = 400
HTTP_UNAUTHORIZED = 401
HTTP_NOT_FOUND = 404
HTTP_INTERNAL_ERROR = 500
HTTP_SERVICE_UNAVAILABLE = 503


def success_response(data: Optional[Dict[str, Any]] = None, 
                    message: Optional[str] = None,
                    status_code: int = HTTP_OK) -> tuple:
    """
    Create a successful JSON response.
    
    Args:
        data: Response data dictionary
        message: Optional success message
        status_code: HTTP status code
        
    Returns:
        Tuple of (jsonify response, status_code)
    """
    response = {"success": True}
    if message:
        response["message"] = message
    if data:
        response.update(data)
    return jsonify(response), status_code


def error_response(error: Any, 
                  details: Optional[str] = None,
                  status_code: int = HTTP_INTERNAL_ERROR) -> tuple:
    """
    Create an error JSON response.
    
    Args:
        error: Error message (string) or error object (dict)
        details: Optional error details
        status_code: HTTP status code
        
    Returns:
        Tuple of (jsonify response, status_code)
    """
    if isinstance(error, dict):
        # If error is a dict, use it as the response
        response = {"error": error.get("message", str(error))}
        # Add any additional fields from the error dict
        for key, value in error.items():
            if key != "message":
                response[key] = value
    else:
        # If error is a string, use it directly
        response = {"error": str(error)}
    
    if details:
        response["details"] = details
    return jsonify(response), status_code


def paginated_response(items: list, 
                      page: int, 
                      per_page: int, 
                      total: int, 
                      pages: int,
                      data_key: str = "items") -> tuple:
    """
    Create a paginated JSON response.
    
    Args:
        items: List of items for current page
        page: Current page number
        per_page: Items per page
        total: Total number of items
        pages: Total number of pages
        data_key: Key name for items in response
        
    Returns:
        Tuple of (jsonify response, status_code)
    """
    return success_response({
        data_key: items,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": pages
        }
    })


def handle_exception(exception: Exception, 
                    context: str,
                    status_code: int = HTTP_INTERNAL_ERROR) -> tuple:
    """
    Handle exceptions and return error response.
    
    Args:
        exception: Exception object
        context: Context description for logging
        status_code: HTTP status code
        
    Returns:
        Tuple of (jsonify response, status_code)
    """
    logger.error(f"{context} error: {exception}", exc_info=True)
    return error_response(str(exception), status_code=status_code)

