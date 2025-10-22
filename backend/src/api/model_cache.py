"""Model Cache Management API endpoints."""

from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import AdminUser, CurrentUser
from src.database.session import get_db
from src.services.ai.model_cache_manager import get_model_cache_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/cache/stats",
    summary="Get model cache statistics",
    description="Get statistics about cached AI models (Admin only)"
)
async def get_cache_stats(
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Get model cache statistics."""
    try:
        cache_manager = get_model_cache_manager()
        stats = cache_manager.get_cache_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get cache statistics"
        )


@router.get(
    "/cache/validate",
    summary="Validate model cache",
    description="Validate integrity of cached models (Admin only)"
)
async def validate_cache(
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Validate model cache integrity."""
    try:
        cache_manager = get_model_cache_manager()
        validation_results = cache_manager.validate_cache()
        return {"success": True, "data": validation_results}
    except Exception as e:
        logger.error(f"Failed to validate cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate cache"
        )


@router.delete(
    "/cache/clear",
    summary="Clear model cache",
    description="Clear all cached models (Admin only)"
)
async def clear_all_cache(
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Clear all model cache."""
    try:
        cache_manager = get_model_cache_manager()
        cache_manager.clear_cache()
        logger.info("Model cache cleared by admin")
        return {"success": True, "message": "Model cache cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )


@router.delete(
    "/cache/clear/{model_name}",
    summary="Clear specific model cache",
    description="Clear cache for specific model (Admin only)"
)
async def clear_model_cache(
    model_name: str,
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Clear cache for specific model."""
    try:
        cache_manager = get_model_cache_manager()
        cache_manager.clear_cache(model_name)
        logger.info(f"Model cache cleared for: {model_name}")
        return {"success": True, "message": f"Cache cleared for model: {model_name}"}
    except Exception as e:
        logger.error(f"Failed to clear cache for {model_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache for model: {model_name}"
        )


@router.post(
    "/cache/preload",
    summary="Preload models",
    description="Preload all AI models into cache (Admin only)"
)
async def preload_models(
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Preload all AI models into cache."""
    try:
        cache_manager = get_model_cache_manager()
        
        # Get list of available models
        available_models = list(cache_manager.model_registry.keys())
        preloaded_models = []
        failed_models = []
        
        for model_name in available_models:
            try:
                # Try to load model (will cache if not already cached)
                model = cache_manager.get_or_create_model(model_name)
                if model is not None:
                    preloaded_models.append(model_name)
                else:
                    failed_models.append(model_name)
            except Exception as e:
                logger.warning(f"Failed to preload {model_name}: {e}")
                failed_models.append(model_name)
        
        logger.info(f"Preloaded {len(preloaded_models)} models, {len(failed_models)} failed")
        
        return {
            "success": True,
            "message": f"Preloaded {len(preloaded_models)} models",
            "preloaded": preloaded_models,
            "failed": failed_models
        }
        
    except Exception as e:
        logger.error(f"Failed to preload models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to preload models"
        )


@router.get(
    "/cache/models",
    summary="List available models",
    description="List all available AI models in registry"
)
async def list_available_models(
    current_user: CurrentUser = None,
    db: AsyncSession = Depends(get_db),
):
    """List all available AI models."""
    try:
        cache_manager = get_model_cache_manager()
        
        models_info = []
        for model_name, model_info in cache_manager.model_registry.items():
            is_cached = cache_manager.is_model_cached(model_name)
            
            models_info.append({
                "name": model_name,
                "type": model_info["type"],
                "version": model_info["version"],
                "device_dependent": model_info.get("device_dependent", True),
                "cached": is_cached,
                "description": f"{model_info['type']} model for {model_name}"
            })
        
        return {
            "success": True,
            "data": {
                "total_models": len(models_info),
                "models": models_info
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list available models"
        )


@router.post(
    "/cache/warmup",
    summary="Warm up models",
    description="Warm up specific models for faster inference (Admin only)"
)
async def warmup_models(
    model_names: List[str],
    admin_user: AdminUser = None,
    db: AsyncSession = Depends(get_db),
):
    """Warm up specific models."""
    try:
        cache_manager = get_model_cache_manager()
        
        warmed_up = []
        failed = []
        
        for model_name in model_names:
            try:
                # Load model to warm up
                model = cache_manager.get_or_create_model(model_name)
                if model is not None:
                    warmed_up.append(model_name)
                else:
                    failed.append(model_name)
            except Exception as e:
                logger.warning(f"Failed to warm up {model_name}: {e}")
                failed.append(model_name)
        
        return {
            "success": True,
            "message": f"Warmed up {len(warmed_up)} models",
            "warmed_up": warmed_up,
            "failed": failed
        }
        
    except Exception as e:
        logger.error(f"Failed to warm up models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to warm up models"
        )
