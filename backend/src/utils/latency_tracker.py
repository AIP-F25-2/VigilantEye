"""Utility module for API latency tracking with percentile calculation."""

import collections
import threading
from typing import Dict, List, Optional

import numpy as np


class LatencyTracker:
    """Thread-safe latency tracker with percentile calculation."""

    _instance: Optional["LatencyTracker"] = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern - ensures single shared instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_samples: int = 1000):
        """Initialize latency tracker with configurable max samples."""
        if getattr(self, "_initialized", False):
            return

        self.latency_data = collections.defaultdict(
            lambda: collections.deque(maxlen=max_samples)
        )
        self.lock = threading.Lock()
        self.max_samples = max_samples
        self._initialized = True

    def add_latency(self, endpoint: str, duration_ms: float) -> None:
        """Add latency measurement for an endpoint."""
        with self.lock:
            self.latency_data[endpoint].append(duration_ms)

    def get_percentiles(self, endpoint: Optional[str] = None) -> Dict[str, float]:
        """Calculate latency percentiles for endpoint(s).

        Args:
            endpoint: Specific endpoint to calculate percentiles for.
                     If None, aggregates all endpoints.

        Returns:
            Dictionary with p50, p95, p99, and count.
        """
        with self.lock:
            if endpoint:
                latencies = list(self.latency_data[endpoint])
            else:
                # Aggregate all endpoints
                latencies = []
                for deque in self.latency_data.values():
                    latencies.extend(deque)

            if not latencies:
                return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "count": 0}

            p50 = float(np.percentile(latencies, 50))
            p95 = float(np.percentile(latencies, 95))
            p99 = float(np.percentile(latencies, 99))

            return {
                "p50": round(p50, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
                "count": len(latencies),
            }

    def get_all_endpoints(self) -> List[str]:
        """Return list of all tracked endpoints."""
        with self.lock:
            return list(self.latency_data.keys())

    def reset(self) -> None:
        """Clear all latency data."""
        with self.lock:
            self.latency_data.clear()

