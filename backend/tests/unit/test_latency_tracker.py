"""Unit tests for LatencyTracker utility."""

import threading
import time

import pytest

from src.utils.latency_tracker import LatencyTracker


@pytest.fixture
def latency_tracker():
    """Create a fresh LatencyTracker instance for each test."""
    tracker = LatencyTracker(max_samples=1000)
    tracker.reset()
    return tracker


def test_add_latency_single_endpoint(latency_tracker):
    """Test adding latencies for a single endpoint."""
    latency_tracker.add_latency("/api/videos", 100.0)
    latency_tracker.add_latency("/api/videos", 200.0)
    latency_tracker.add_latency("/api/videos", 150.0)

    percentiles = latency_tracker.get_percentiles("/api/videos")

    assert percentiles["count"] == 3
    assert percentiles["p50"] == 150.0  # Median of [100, 150, 200]
    assert percentiles["p95"] > 150.0
    assert percentiles["p99"] > 150.0


def test_add_latency_multiple_endpoints(latency_tracker):
    """Test adding latencies for multiple endpoints."""
    latency_tracker.add_latency("/api/videos", 100.0)
    latency_tracker.add_latency("/api/tickets", 200.0)
    latency_tracker.add_latency("/api/auth", 300.0)

    # Get percentiles for specific endpoint
    percentiles = latency_tracker.get_percentiles("/api/videos")
    assert percentiles["count"] == 1
    assert percentiles["p50"] == 100.0

    # Get percentiles for all endpoints
    percentiles_all = latency_tracker.get_percentiles()
    assert percentiles_all["count"] == 3


def test_add_latency_max_samples_limit(latency_tracker):
    """Test that max_samples limit is enforced."""
    # Add more than max_samples
    for i in range(1500):
        latency_tracker.add_latency("/api/videos", float(i))

    percentiles = latency_tracker.get_percentiles("/api/videos")

    # Should only keep last 1000 samples
    assert percentiles["count"] == 1000
    # Oldest values (0-499) should be dropped, so min should be around 500
    assert percentiles["p50"] >= 500.0


def test_get_percentiles_no_data(latency_tracker):
    """Test getting percentiles when no data exists."""
    percentiles = latency_tracker.get_percentiles()

    assert percentiles["p50"] == 0.0
    assert percentiles["p95"] == 0.0
    assert percentiles["p99"] == 0.0
    assert percentiles["count"] == 0


def test_get_percentiles_single_value(latency_tracker):
    """Test percentiles calculation with single value."""
    latency_tracker.add_latency("/api/videos", 100.0)

    percentiles = latency_tracker.get_percentiles("/api/videos")

    # All percentiles should be the same for single value
    assert percentiles["p50"] == 100.0
    assert percentiles["p95"] == 100.0
    assert percentiles["p99"] == 100.0
    assert percentiles["count"] == 1


def test_get_all_endpoints(latency_tracker):
    """Test getting list of all tracked endpoints."""
    latency_tracker.add_latency("/api/videos", 100.0)
    latency_tracker.add_latency("/api/tickets", 200.0)
    latency_tracker.add_latency("/api/auth", 300.0)

    endpoints = latency_tracker.get_all_endpoints()

    assert len(endpoints) == 3
    assert "/api/videos" in endpoints
    assert "/api/tickets" in endpoints
    assert "/api/auth" in endpoints


def test_reset_clears_all_data(latency_tracker):
    """Test that reset clears all latency data."""
    latency_tracker.add_latency("/api/videos", 100.0)
    latency_tracker.add_latency("/api/tickets", 200.0)

    latency_tracker.reset()

    percentiles = latency_tracker.get_percentiles()
    assert percentiles["count"] == 0

    endpoints = latency_tracker.get_all_endpoints()
    assert len(endpoints) == 0


def test_thread_safety(latency_tracker):
    """Test that latency tracker is thread-safe."""
    def add_latencies(thread_id: int, count: int):
        for i in range(count):
            latency_tracker.add_latency(f"/api/endpoint{thread_id}", float(i))

    # Create 10 threads, each adding 100 latencies
    threads = []
    for thread_id in range(10):
        thread = threading.Thread(target=add_latencies, args=(thread_id, 100))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Check that all latencies were added (max_samples may limit total)
    percentiles = latency_tracker.get_percentiles()
    assert percentiles["count"] > 0
    assert percentiles["count"] <= 1000  # Max samples enforced

    # Check all endpoints exist
    endpoints = latency_tracker.get_all_endpoints()
    assert len(endpoints) == 10


def test_percentile_calculation_accuracy(latency_tracker):
    """Test percentile calculation accuracy with known values."""
    # Add known latencies
    known_latencies = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    for latency in known_latencies:
        latency_tracker.add_latency("/api/test", float(latency))

    percentiles = latency_tracker.get_percentiles("/api/test")

    # p50 should be approximately 55 (median)
    assert 50 <= percentiles["p50"] <= 60

    # p95 should be approximately 95
    assert 90 <= percentiles["p95"] <= 100

    # p99 should be approximately 99
    assert 95 <= percentiles["p99"] <= 100

    assert percentiles["count"] == 10


def test_singleton_pattern():
    """Test that LatencyTracker follows singleton pattern."""
    tracker1 = LatencyTracker()
    tracker2 = LatencyTracker()

    # Should be the same instance
    assert tracker1 is tracker2

    # Adding to one should be visible in the other
    tracker1.add_latency("/api/test", 100.0)
    percentiles = tracker2.get_percentiles("/api/test")
    assert percentiles["count"] == 1

