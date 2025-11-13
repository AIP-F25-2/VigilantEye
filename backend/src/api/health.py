"""Health monitoring and metrics endpoints for VigilantEye backend."""

import collections
import logging
import shutil
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import numpy as np
import redis
from flask import Blueprint, Response, jsonify, request

from src.app import db
from src.celery_app import create_celery_app
from src.config.settings import get_config
from src.models.ai_performance_metrics import AIPerformanceMetrics
from src.utils.chromadb_manager import ChromaDBManager
from src.utils.db_utils import check_db_connection
from src.utils.latency_tracker import LatencyTracker

health_bp = Blueprint("health", __name__)
config = get_config()
logger = logging.getLogger(__name__)

# Latency tracker will be accessed via singleton pattern
# Same instance is used in app.py middleware

# Celery app will be lazily initialized when needed
_celery_app = None
_celery_app_lock = threading.Lock()

# Health check cache to reduce overhead from frequent probing
_health_check_cache = {}
_health_check_cache_lock = threading.Lock()


def _get_celery_app():
    """Get or create Celery app instance (lazy initialization)."""
    global _celery_app
    if _celery_app is None:
        with _celery_app_lock:
            if _celery_app is None:
                _celery_app = create_celery_app()
    return _celery_app


def _get_cached_check(check_name: str, check_func):
    """Get cached health check result or execute and cache it."""
    cache_ttl = getattr(config, "HEALTH_CHECK_CACHE_SECONDS", 10)
    current_time = time.time()
    
    with _health_check_cache_lock:
        cached_entry = _health_check_cache.get(check_name)
        if cached_entry and (current_time - cached_entry["timestamp"]) < cache_ttl:
            return cached_entry["result"]
        
        # Execute check and cache result
        result = check_func()
        _health_check_cache[check_name] = {
            "result": result,
            "timestamp": current_time,
        }
        return result


@health_bp.route("/health", methods=["GET"])
def health():
    """Liveness check - is the application running?"""
    return (
        jsonify(
            {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        ),
        200,
    )


@health_bp.route("/health/ready", methods=["GET"])
def health_ready():
    """Readiness check - are all dependencies available?"""
    checks = [
        _check_mysql(),
        _check_redis(),
        _check_chromadb(),
        _check_celery(),
        _check_storage(),
    ]

    ready = all(check["status"] == "pass" for check in checks)

    status_code = 200 if ready else 503

    return (
        jsonify(
            {
                "ready": ready,
                "checks": checks,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        ),
        status_code,
    )


@health_bp.route("/metrics", methods=["GET"])
def metrics():
    """Expose performance metrics in Prometheus format or JSON."""
    accept_header = request.headers.get("Accept", "")

    # Collect all metrics
    api_latency = _calculate_api_latency_percentiles()
    ai_inference_times = _get_ai_inference_times()
    database_pool = _get_database_pool_stats()
    storage_usage = _check_storage()
    celery_stats = _check_celery()

    metrics_data = {
        "api_latency": api_latency,
        "ai_inference_times": ai_inference_times,
        "database_pool": database_pool,
        "storage_usage": {
            "total_bytes": storage_usage.get("total_bytes", 0),
            "used_bytes": storage_usage.get("used_bytes", 0),
            "free_bytes": storage_usage.get("free_bytes", 0),
            "percentage": storage_usage.get("percentage", 0.0),
        },
        "celery": {
            "workers": celery_stats.get("workers", 0),
            "active_tasks": celery_stats.get("active_tasks", 0),
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Return Prometheus format if requested
    if "text/plain" in accept_header or "application/openmetrics-text" in accept_header:
        prometheus_body = _format_prometheus_metrics(metrics_data)
        return Response(prometheus_body, mimetype="text/plain; charset=utf-8"), 200

    # Return JSON format (default)
    return jsonify(metrics_data), 200


def _check_mysql() -> Dict[str, Any]:
    """Check MySQL database connectivity."""
    try:
        start = time.perf_counter()
        is_connected, message = check_db_connection(db.session)
        response_time_ms = (time.perf_counter() - start) * 1000

        return {
            "name": "mysql",
            "status": "pass" if is_connected else "fail",
            "message": message,
            "response_time_ms": round(response_time_ms, 2),
        }
    except Exception as exc:
        logger.exception("MySQL health check failed", extra={"context": {"error": str(exc)}})
        return {
            "name": "mysql",
            "status": "fail",
            "message": str(exc),
            "response_time_ms": 0.0,
        }


def _check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        redis_client = redis.from_url(config.REDIS_URL, decode_responses=True)
        start = time.perf_counter()
        redis_client.ping()
        response_time_ms = (time.perf_counter() - start) * 1000

        return {
            "name": "redis",
            "status": "pass",
            "response_time_ms": round(response_time_ms, 2),
        }
    except redis.exceptions.ConnectionError as exc:
        logger.warning("Redis health check failed", extra={"context": {"error": str(exc)}})
        return {
            "name": "redis",
            "status": "fail",
            "message": str(exc),
            "response_time_ms": 0.0,
        }
    except Exception as exc:
        logger.exception("Redis health check failed", extra={"context": {"error": str(exc)}})
        return {
            "name": "redis",
            "status": "fail",
            "message": str(exc),
            "response_time_ms": 0.0,
        }


def _check_chromadb() -> Dict[str, Any]:
    """Check ChromaDB connectivity."""
    def _do_check():
        try:
            chromadb_manager = ChromaDBManager()
            start = time.perf_counter()
            stats = chromadb_manager.get_collection_stats()
            response_time_ms = (time.perf_counter() - start) * 1000

            return {
                "name": "chromadb",
                "status": "pass",
                "response_time_ms": round(response_time_ms, 2),
                "collections": stats,
            }
        except Exception as exc:
            logger.exception("ChromaDB health check failed", extra={"context": {"error": str(exc)}})
            return {
                "name": "chromadb",
                "status": "fail",
                "message": str(exc),
                "response_time_ms": 0.0,
            }
    
    return _get_cached_check("chromadb", _do_check)


def _check_celery() -> Dict[str, Any]:
    """Check Celery workers and active tasks."""
    def _do_check():
        try:
            celery_app = _get_celery_app()
            inspect = celery_app.control.inspect()
            workers = inspect.active_workers() or {}
            worker_count = len(workers)

            active_tasks = inspect.active() or {}
            task_count = sum(len(tasks) for tasks in active_tasks.values())

            return {
                "name": "celery",
                "status": "pass" if worker_count > 0 else "fail",
                "workers": worker_count,
                "active_tasks": task_count,
            }
        except Exception as exc:
            logger.exception("Celery health check failed", extra={"context": {"error": str(exc)}})
            return {
                "name": "celery",
                "status": "fail",
                "workers": 0,
                "active_tasks": 0,
                "message": str(exc),
            }
    
    return _get_cached_check("celery", _do_check)


def _check_storage() -> Dict[str, Any]:
    """Check storage disk usage."""
    def _do_check():
        try:
            storage_path = config.STORAGE_BASE_PATH
            total, used, free = shutil.disk_usage(storage_path)
            percentage = (used / total) * 100 if total > 0 else 0.0

            warning_threshold = getattr(config, "STORAGE_WARNING_THRESHOLD", 80)
            status = "pass" if percentage < warning_threshold else "fail"

            return {
                "name": "storage",
                "status": status,
                "total_bytes": total,
                "used_bytes": used,
                "free_bytes": free,
                "percentage": round(percentage, 2),
            }
        except OSError as exc:
            logger.exception("Storage health check failed", extra={"context": {"error": str(exc)}})
            return {
                "name": "storage",
                "status": "fail",
                "message": str(exc),
                "total_bytes": 0,
                "used_bytes": 0,
                "free_bytes": 0,
                "percentage": 0.0,
            }
        except Exception as exc:
            logger.exception("Storage health check failed", extra={"context": {"error": str(exc)}})
            return {
                "name": "storage",
                "status": "fail",
                "message": str(exc),
                "total_bytes": 0,
                "used_bytes": 0,
                "free_bytes": 0,
                "percentage": 0.0,
            }
    
    return _get_cached_check("storage", _do_check)


def _get_ai_inference_times() -> Dict[str, float]:
    """Get average AI inference times for last 24 hours."""
    try:
        history_hours = getattr(config, "METRICS_HISTORY_HOURS", 24)
        cutoff_time = datetime.utcnow() - timedelta(hours=history_hours)

        metrics = (
            AIPerformanceMetrics.query.filter(
                AIPerformanceMetrics.created_at >= cutoff_time,
                AIPerformanceMetrics.status == "success",
                AIPerformanceMetrics.is_deleted == False,
            )
            .all()
        )

        # Group by task_name
        grouped = collections.defaultdict(list)
        for metric in metrics:
            grouped[metric.task_name].append(metric.duration_ms)

        # Calculate averages
        ai_times = {}
        task_names = [
            "person_detection",
            "scene_analysis",
            "object_detection",
            "speech_to_text",
            "audio_classification",
            "llm_analysis",
        ]

        for task_name in task_names:
            durations = grouped.get(task_name, [])
            avg = sum(durations) / len(durations) if durations else 0.0
            ai_times[task_name] = round(avg, 2)

        return ai_times
    except Exception as exc:
        logger.exception("Failed to get AI inference times", extra={"context": {"error": str(exc)}})
        return {
            "person_detection": 0.0,
            "scene_analysis": 0.0,
            "object_detection": 0.0,
            "speech_to_text": 0.0,
            "audio_classification": 0.0,
            "llm_analysis": 0.0,
        }


def _calculate_api_latency_percentiles() -> Dict[str, float]:
    """Calculate API latency percentiles from latency tracker."""
    try:
        # Use the singleton instance (same as in app.py middleware)
        tracker = LatencyTracker()
        percentiles = tracker.get_percentiles()
        return {
            "p50": percentiles.get("p50", 0.0),
            "p95": percentiles.get("p95", 0.0),
            "p99": percentiles.get("p99", 0.0),
        }
    except Exception as exc:
        logger.exception("Failed to calculate latency percentiles", extra={"context": {"error": str(exc)}})
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0}


def _get_database_pool_stats() -> Dict[str, Any]:
    """Get database connection pool statistics."""
    try:
        from src.utils.db_utils import get_pool_stats

        stats = get_pool_stats(db.engine)
        return {
            "size": stats.get("pool_size", 0),
            "checked_out": stats.get("checked_out", 0),
            "overflow": stats.get("overflow", 0),
            "checked_in": stats.get("checked_in", 0),
        }
    except Exception as exc:
        logger.exception("Failed to get database pool stats", extra={"context": {"error": str(exc)}})
        return {
            "size": 0,
            "checked_out": 0,
            "overflow": 0,
            "checked_in": 0,
        }


def _format_prometheus_metrics(metrics_data: Dict[str, Any]) -> str:
    """Format metrics data as Prometheus text format."""
    lines = []

    # API Latency
    lines.append("# HELP api_latency_p50_ms API latency 50th percentile in milliseconds")
    lines.append("# TYPE api_latency_p50_ms gauge")
    lines.append(f"api_latency_p50_ms {metrics_data['api_latency']['p50']}")

    lines.append("# HELP api_latency_p95_ms API latency 95th percentile in milliseconds")
    lines.append("# TYPE api_latency_p95_ms gauge")
    lines.append(f"api_latency_p95_ms {metrics_data['api_latency']['p95']}")

    lines.append("# HELP api_latency_p99_ms API latency 99th percentile in milliseconds")
    lines.append("# TYPE api_latency_p99_ms gauge")
    lines.append(f"api_latency_p99_ms {metrics_data['api_latency']['p99']}")

    # AI Inference Times
    lines.append("# HELP ai_inference_time_ms Average AI inference time in milliseconds")
    lines.append("# TYPE ai_inference_time_ms gauge")
    for task_name, duration in metrics_data["ai_inference_times"].items():
        lines.append(f'ai_inference_time_ms{{task="{task_name}"}} {duration}')

    # Database Pool
    lines.append("# HELP db_pool_size Database connection pool size")
    lines.append("# TYPE db_pool_size gauge")
    lines.append(f"db_pool_size {metrics_data['database_pool']['size']}")

    lines.append("# HELP db_pool_checked_out Database connections checked out")
    lines.append("# TYPE db_pool_checked_out gauge")
    lines.append(f"db_pool_checked_out {metrics_data['database_pool']['checked_out']}")

    # Storage
    lines.append("# HELP storage_usage_percentage Storage disk usage percentage")
    lines.append("# TYPE storage_usage_percentage gauge")
    lines.append(f"storage_usage_percentage {metrics_data['storage_usage']['percentage']}")

    # Celery
    lines.append("# HELP celery_workers Number of active Celery workers")
    lines.append("# TYPE celery_workers gauge")
    lines.append(f"celery_workers {metrics_data['celery']['workers']}")

    lines.append("# HELP celery_active_tasks Number of active Celery tasks")
    lines.append("# TYPE celery_active_tasks gauge")
    lines.append(f"celery_active_tasks {metrics_data['celery']['active_tasks']}")

    return "\n".join(lines) + "\n"

