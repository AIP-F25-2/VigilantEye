"""Global error handling middleware."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from src.utils.exceptions import AppException
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def error_handler_middleware(request: Request, call_next):
    """
    Global error handler middleware.
    
    Catches all exceptions and returns standardized error responses.
    """
    try:
        return await call_next(request)
    except AppException as exc:
        logger.warning(
            f"Application exception: {exc.message}",
            extra={"code": exc.code, "detail": exc.detail}
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "detail": exc.detail,
                "code": exc.code,
            },
        )
    except Exception as exc:
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "detail": str(exc) if request.app.state.settings.app_debug else None,
                "code": "INTERNAL_ERROR",
            },
        )
