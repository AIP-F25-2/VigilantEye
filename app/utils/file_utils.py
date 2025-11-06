"""
File upload utilities for VIGILANTEye
Centralized file handling to eliminate code duplication
"""

import os
import time
import logging
from flask import current_app
from werkzeug.utils import secure_filename
from typing import Optional, Set

logger = logging.getLogger(__name__)

# Constants
MILLISECONDS_PER_SECOND = 1000
DEFAULT_UPLOAD_FOLDER = 'uploads'
DEFAULT_FRAME_SKIP = 30
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'wmv', 'flv', 'webm'}


def is_allowed_file(filename: str, allowed_extensions: Set[str]) -> bool:
    """
    Check if file extension is allowed.
    
    Args:
        filename: Name of the file
        allowed_extensions: Set of allowed extensions
        
    Returns:
        True if extension is allowed, False otherwise
    """
    if not filename or '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in allowed_extensions


def save_uploaded_file(file, subfolder: str = DEFAULT_UPLOAD_FOLDER, 
                       allowed_extensions: Optional[Set[str]] = None) -> Optional[str]:
    """
    Save uploaded file and return path.
    
    Args:
        file: File object from request
        subfolder: Subfolder within upload directory
        allowed_extensions: Set of allowed extensions (defaults to images)
        
    Returns:
        File path if successful, None otherwise
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_IMAGE_EXTENSIONS
    
    if not file or not file.filename:
        return None
    
    if not is_allowed_file(file.filename, allowed_extensions):
        return None
    
    try:
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        timestamp = int(time.time())
        filename = f"{name}_{timestamp}{ext}"
        
        upload_dir = os.path.join(
            current_app.config.get('UPLOAD_FOLDER', DEFAULT_UPLOAD_FOLDER), 
            subfolder
        )
        os.makedirs(upload_dir, exist_ok=True)
        
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        return filepath
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return None


def calculate_processing_time(start_time: float) -> float:
    """
    Calculate processing time in milliseconds.
    
    Args:
        start_time: Start time from time.time()
        
    Returns:
        Processing time in milliseconds
    """
    return (time.time() - start_time) * MILLISECONDS_PER_SECOND


def validate_file_upload(request_files, required_field: str) -> tuple[Optional[object], Optional[str]]:
    """
    Validate file upload from request.
    
    Args:
        request_files: request.files object
        required_field: Name of the required file field
        
    Returns:
        Tuple of (file_object, error_message). Both None if valid.
    """
    if required_field not in request_files:
        return None, f"No {required_field} file provided"
    
    file = request_files[required_field]
    if not file or file.filename == '':
        return None, "No file selected"
    
    return file, None

