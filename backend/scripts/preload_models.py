"""Model preloading script for faster startup."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent))

from src.services.ai.model_cache_manager import get_model_cache_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def preload_models():
    """Preload all AI models for faster inference."""
    logger.info("Starting model preloading...")
    
    cache_manager = get_model_cache_manager()
    
    # Get cache statistics
    stats = cache_manager.get_cache_stats()
    logger.info(f"Cache stats: {stats}")
    
    # List of critical models to preload
    critical_models = [
        'mtcnn',
        'facenet_resnet', 
        'resnet50',
        'resnet18',
        'efficientnet_b0',
        'yolov8n',
        'easyocr',
        'opencv_hog'
    ]
    
    preloaded_count = 0
    failed_count = 0
    
    for model_name in critical_models:
        try:
            logger.info(f"Preloading model: {model_name}")
            
            # Get or create model (will cache if not already cached)
            model = cache_manager.get_or_create_model(model_name)
            
            if model is not None:
                logger.info(f"✓ Successfully preloaded: {model_name}")
                preloaded_count += 1
            else:
                logger.warning(f"✗ Failed to preload: {model_name}")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"✗ Error preloading {model_name}: {e}")
            failed_count += 1
    
    # Final statistics
    final_stats = cache_manager.get_cache_stats()
    
    logger.info("=" * 50)
    logger.info("MODEL PRELOADING COMPLETE")
    logger.info(f"✓ Successfully preloaded: {preloaded_count} models")
    logger.info(f"✗ Failed to preload: {failed_count} models")
    logger.info(f"📊 Total cached models: {final_stats['total_models']}")
    logger.info(f"💾 Cache size: {final_stats['total_size_mb']} MB")
    logger.info("=" * 50)
    
    return preloaded_count, failed_count


def main():
    """Main function."""
    try:
        preloaded, failed = asyncio.run(preload_models())
        
        if failed > 0:
            logger.warning(f"Some models failed to preload: {failed}")
            sys.exit(1)
        else:
            logger.info("All models preloaded successfully!")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Preloading failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
