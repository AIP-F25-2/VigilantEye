"""Health check and performance metrics API."""

import asyncio
import json
import os
import psutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.database.session import get_db
from src.services.ai.model_cache_manager import get_model_cache_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Health"])
settings = get_settings()

# Global performance metrics
_performance_metrics = {
    'startup_time': None,
    'request_count': 0,
    'total_response_time': 0.0,
    'error_count': 0,
    'last_request_time': None,
    'uptime_start': time.time()
}


def update_request_metrics(response_time: float, is_error: bool = False):
    """Update request performance metrics."""
    global _performance_metrics
    _performance_metrics['request_count'] += 1
    _performance_metrics['total_response_time'] += response_time
    _performance_metrics['last_request_time'] = datetime.utcnow()
    if is_error:
        _performance_metrics['error_count'] += 1


def set_startup_time(startup_time: float):
    """Set application startup time."""
    global _performance_metrics
    _performance_metrics['startup_time'] = startup_time


async def get_system_metrics() -> Dict:
    """Get system performance metrics."""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # Memory metrics
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        
        # Network metrics
        network = psutil.net_io_counters()
        
        return {
            'cpu': {
                'usage_percent': cpu_percent,
                'count': cpu_count,
                'frequency_mhz': cpu_freq.current if cpu_freq else None,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
            },
            'memory': {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'usage_percent': memory.percent,
                'swap_total_gb': round(swap.total / (1024**3), 2),
                'swap_used_gb': round(swap.used / (1024**3), 2)
            },
            'disk': {
                'total_gb': round(disk.total / (1024**3), 2),
                'used_gb': round(disk.used / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'usage_percent': round((disk.used / disk.total) * 100, 2)
            },
            'network': {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv
            }
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return {'error': str(e)}


async def get_application_metrics() -> Dict:
    """Get application-specific metrics."""
    global _performance_metrics
    
    uptime = time.time() - _performance_metrics['uptime_start']
    avg_response_time = (
        _performance_metrics['total_response_time'] / _performance_metrics['request_count']
        if _performance_metrics['request_count'] > 0 else 0
    )
    
    error_rate = (
        (_performance_metrics['error_count'] / _performance_metrics['request_count']) * 100
        if _performance_metrics['request_count'] > 0 else 0
    )
    
    return {
        'uptime_seconds': round(uptime, 2),
        'uptime_human': str(timedelta(seconds=int(uptime))),
        'startup_time_seconds': _performance_metrics['startup_time'],
        'request_count': _performance_metrics['request_count'],
        'error_count': _performance_metrics['error_count'],
        'error_rate_percent': round(error_rate, 2),
        'average_response_time_ms': round(avg_response_time * 1000, 2),
        'last_request_time': _performance_metrics['last_request_time'].isoformat() if _performance_metrics['last_request_time'] else None,
        'requests_per_minute': round(_performance_metrics['request_count'] / (uptime / 60), 2) if uptime > 0 else 0
    }


async def get_database_metrics(db: AsyncSession) -> Dict:
    """Get database performance metrics."""
    try:
        # Test database connection
        start_time = time.time()
        result = await db.execute(text("SELECT 1"))
        await db.commit()
        db_response_time = (time.time() - start_time) * 1000
        
        # Get database size (PostgreSQL specific)
        try:
            size_result = await db.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size
            """))
            db_size = size_result.scalar()
        except:
            db_size = "Unknown"
        
        return {
            'status': 'healthy',
            'response_time_ms': round(db_response_time, 2),
            'size': db_size,
            'connection_pool': {
                'checked_out': db.bind.pool.checkedout() if hasattr(db.bind.pool, 'checkedout') else 'Unknown',
                'overflow': db.bind.pool.overflow() if hasattr(db.bind.pool, 'overflow') else 'Unknown',
                'size': db.bind.pool.size() if hasattr(db.bind.pool, 'size') else 'Unknown'
            }
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'response_time_ms': None
        }


async def get_ai_models_metrics() -> Dict:
    """Get AI models cache metrics."""
    try:
        cache_manager = get_model_cache_manager()
        cache_stats = cache_manager.get_cache_stats()
        validation_results = cache_manager.validate_cache()
        
        return {
            'cache_stats': cache_stats,
            'validation_results': validation_results,
            'total_cached_models': cache_stats.get('total_models', 0),
            'cache_size_mb': cache_stats.get('total_size_mb', 0),
            'healthy_models': sum(1 for v in validation_results.values() if v.get('valid', False)),
            'total_registered_models': len(validation_results)
        }
    except Exception as e:
        logger.error(f"AI models metrics failed: {e}")
        return {'error': str(e)}


async def get_storage_metrics() -> Dict:
    """Get storage metrics."""
    try:
        storage_paths = [
            'storage/videos',
            'storage/evidence', 
            'storage/model_cache',
            'storage/vector_db'
        ]
        
        storage_info = {}
        total_size = 0
        
        for path in storage_paths:
            path_obj = Path(path)
            if path_obj.exists():
                size = sum(f.stat().st_size for f in path_obj.rglob('*') if f.is_file())
                file_count = len(list(path_obj.rglob('*')))
                storage_info[path] = {
                    'size_mb': round(size / (1024**2), 2),
                    'file_count': file_count,
                    'exists': True
                }
                total_size += size
            else:
                storage_info[path] = {
                    'size_mb': 0,
                    'file_count': 0,
                    'exists': False
                }
        
        return {
            'paths': storage_info,
            'total_size_mb': round(total_size / (1024**2), 2),
            'total_size_gb': round(total_size / (1024**3), 2)
        }
    except Exception as e:
        logger.error(f"Storage metrics failed: {e}")
        return {'error': str(e)}


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Simple health check endpoint"
)
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": settings.app_name,
        "environment": settings.app_env,
        "version": "1.0.0"
    }


@router.get(
    "/health/detailed",
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Comprehensive health check with all metrics"
)
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Detailed health check with performance metrics."""
    start_time = time.time()
    
    try:
        # Gather all metrics in parallel
        system_metrics, app_metrics, db_metrics, ai_metrics, storage_metrics = await asyncio.gather(
            get_system_metrics(),
            get_application_metrics(),
            get_database_metrics(db),
            get_ai_models_metrics(),
            get_storage_metrics(),
            return_exceptions=True
        )
        
        # Calculate overall health status
        overall_status = "healthy"
        issues = []
        
        if isinstance(system_metrics, Exception):
            overall_status = "degraded"
            issues.append("System metrics failed")
        
        if isinstance(db_metrics, Exception) or db_metrics.get('status') != 'healthy':
            overall_status = "unhealthy"
            issues.append("Database unhealthy")
        
        if isinstance(ai_metrics, Exception):
            overall_status = "degraded"
            issues.append("AI models metrics failed")
        
        # Check critical thresholds
        if isinstance(system_metrics, dict):
            if system_metrics.get('cpu', {}).get('usage_percent', 0) > 90:
                overall_status = "degraded"
                issues.append("High CPU usage")
            
            if system_metrics.get('memory', {}).get('usage_percent', 0) > 90:
                overall_status = "degraded"
                issues.append("High memory usage")
            
            if system_metrics.get('disk', {}).get('usage_percent', 0) > 90:
                overall_status = "degraded"
                issues.append("High disk usage")
        
        response_time = time.time() - start_time
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": round(response_time * 1000, 2),
            "issues": issues,
            "service": settings.app_name,
            "environment": settings.app_env,
            "version": "1.0.0",
            "metrics": {
                "system": system_metrics if not isinstance(system_metrics, Exception) else {"error": str(system_metrics)},
                "application": app_metrics,
                "database": db_metrics if not isinstance(db_metrics, Exception) else {"error": str(db_metrics)},
                "ai_models": ai_metrics if not isinstance(ai_metrics, Exception) else {"error": str(ai_metrics)},
                "storage": storage_metrics if not isinstance(storage_metrics, Exception) else {"error": str(storage_metrics)}
            }
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get(
    "/health/metrics",
    status_code=status.HTTP_200_OK,
    summary="Performance metrics",
    description="Get detailed performance metrics"
)
async def get_metrics(db: AsyncSession = Depends(get_db)):
    """Get detailed performance metrics."""
    try:
        metrics = await asyncio.gather(
            get_system_metrics(),
            get_application_metrics(),
            get_database_metrics(db),
            get_ai_models_metrics(),
            get_storage_metrics(),
            return_exceptions=True
        )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": metrics[0] if not isinstance(metrics[0], Exception) else {"error": str(metrics[0])},
            "application": metrics[1],
            "database": metrics[2] if not isinstance(metrics[2], Exception) else {"error": str(metrics[2])},
            "ai_models": metrics[3] if not isinstance(metrics[3], Exception) else {"error": str(metrics[3])},
            "storage": metrics[4] if not isinstance(metrics[4], Exception) else {"error": str(metrics[4])}
        }
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to collect metrics: {str(e)}"
        )


@router.get(
    "/health/readiness",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Kubernetes readiness probe endpoint"
)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check for Kubernetes."""
    try:
        # Check database connection
        await db.execute(text("SELECT 1"))
        
        # Check if critical services are available
        cache_manager = get_model_cache_manager()
        
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Service not ready: {str(e)}"
        )


@router.get(
    "/health/liveness",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe", 
    description="Kubernetes liveness probe endpoint"
)
async def liveness_check():
    """Liveness check for Kubernetes."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get(
    "/health/db",
    status_code=status.HTTP_200_OK,
    summary="Database health check",
    description="Check if database connection is healthy"
)
async def database_health_check(db: AsyncSession = Depends(get_db)):
    """Database health check endpoint."""
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
        }