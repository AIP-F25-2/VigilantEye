"""
Performance testing utilities and benchmarks.
"""

import time
import asyncio
import statistics
from typing import List, Dict, Any
import aiohttp
import psutil
import logging

logger = logging.getLogger(__name__)

class PerformanceBenchmark:
    """Performance benchmarking utilities."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []
    
    async def benchmark_endpoint(self, endpoint: str, method: str = "GET", 
                                data: Dict[str, Any] = None, 
                                headers: Dict[str, str] = None,
                                iterations: int = 100) -> Dict[str, Any]:
        """Benchmark a single endpoint."""
        
        response_times = []
        status_codes = []
        errors = []
        
        async with aiohttp.ClientSession() as session:
            for i in range(iterations):
                start_time = time.time()
                
                try:
                    if method.upper() == "GET":
                        async with session.get(f"{self.base_url}{endpoint}", headers=headers) as response:
                            status_codes.append(response.status)
                            await response.text()
                    elif method.upper() == "POST":
                        async with session.post(f"{self.base_url}{endpoint}", 
                                              json=data, headers=headers) as response:
                            status_codes.append(response.status)
                            await response.text()
                    
                    response_time = (time.time() - start_time) * 1000  # Convert to ms
                    response_times.append(response_time)
                    
                except Exception as e:
                    errors.append(str(e))
                    response_times.append(None)
                
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.01)
        
        # Calculate statistics
        valid_times = [t for t in response_times if t is not None]
        
        if valid_times:
            stats = {
                'endpoint': endpoint,
                'method': method,
                'iterations': iterations,
                'successful_requests': len(valid_times),
                'failed_requests': len(errors),
                'success_rate': len(valid_times) / iterations * 100,
                'avg_response_time': statistics.mean(valid_times),
                'median_response_time': statistics.median(valid_times),
                'min_response_time': min(valid_times),
                'max_response_time': max(valid_times),
                'p95_response_time': self._percentile(valid_times, 95),
                'p99_response_time': self._percentile(valid_times, 99),
                'status_codes': self._count_status_codes(status_codes),
                'errors': errors[:5]  # First 5 errors
            }
        else:
            stats = {
                'endpoint': endpoint,
                'method': method,
                'iterations': iterations,
                'successful_requests': 0,
                'failed_requests': len(errors),
                'success_rate': 0,
                'errors': errors
            }
        
        self.results.append(stats)
        return stats
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def _count_status_codes(self, status_codes: List[int]) -> Dict[int, int]:
        """Count status codes."""
        counts = {}
        for code in status_codes:
            counts[code] = counts.get(code, 0) + 1
        return counts
    
    async def benchmark_auth_flow(self, iterations: int = 50) -> Dict[str, Any]:
        """Benchmark authentication flow."""
        results = {}
        
        # Register
        register_data = {
            "username": "perftest",
            "email": "perftest@example.com",
            "password": "testpassword123",
            "role": "user"
        }
        
        results['register'] = await self.benchmark_endpoint(
            "/api/auth/register", "POST", register_data, iterations=iterations
        )
        
        # Login
        login_data = {
            "username": "perftest",
            "password": "testpassword123"
        }
        
        results['login'] = await self.benchmark_endpoint(
            "/api/auth/login", "POST", login_data, iterations=iterations
        )
        
        return results
    
    async def benchmark_video_operations(self, iterations: int = 20) -> Dict[str, Any]:
        """Benchmark video operations."""
        results = {}
        
        # Get videos list
        results['get_videos'] = await self.benchmark_endpoint(
            "/api/videos", iterations=iterations
        )
        
        # Get video status (assuming video ID 1 exists)
        results['get_video_status'] = await self.benchmark_endpoint(
            "/api/video/1", iterations=iterations
        )
        
        return results
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics."""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'network_io': psutil.net_io_counters()._asdict(),
            'process_count': len(psutil.pids())
        }
    
    def generate_report(self) -> str:
        """Generate performance report."""
        report = []
        report.append("=" * 80)
        report.append("PERFORMANCE BENCHMARK REPORT")
        report.append("=" * 80)
        report.append(f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total tests: {len(self.results)}")
        report.append("")
        
        # System metrics
        system_metrics = self.get_system_metrics()
        report.append("SYSTEM METRICS:")
        report.append("-" * 40)
        for key, value in system_metrics.items():
            report.append(f"{key}: {value}")
        report.append("")
        
        # Test results
        for result in self.results:
            report.append(f"ENDPOINT: {result['method']} {result['endpoint']}")
            report.append("-" * 40)
            report.append(f"Iterations: {result['iterations']}")
            report.append(f"Success Rate: {result['success_rate']:.2f}%")
            
            if 'avg_response_time' in result:
                report.append(f"Average Response Time: {result['avg_response_time']:.2f}ms")
                report.append(f"Median Response Time: {result['median_response_time']:.2f}ms")
                report.append(f"95th Percentile: {result['p95_response_time']:.2f}ms")
                report.append(f"99th Percentile: {result['p99_response_time']:.2f}ms")
                report.append(f"Min Response Time: {result['min_response_time']:.2f}ms")
                report.append(f"Max Response Time: {result['max_response_time']:.2f}ms")
            
            if result['status_codes']:
                report.append("Status Codes:")
                for code, count in result['status_codes'].items():
                    report.append(f"  {code}: {count}")
            
            if result['errors']:
                report.append("Errors:")
                for error in result['errors']:
                    report.append(f"  {error}")
            
            report.append("")
        
        return "\n".join(report)

class LoadTestRunner:
    """Run comprehensive load tests."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.benchmark = PerformanceBenchmark(base_url)
    
    async def run_full_load_test(self) -> Dict[str, Any]:
        """Run comprehensive load test."""
        results = {}
        
        logger.info("Starting full load test...")
        
        # Test authentication flow
        logger.info("Testing authentication flow...")
        results['auth'] = await self.benchmark.benchmark_auth_flow(iterations=100)
        
        # Test video operations
        logger.info("Testing video operations...")
        results['video'] = await self.benchmark.benchmark_video_operations(iterations=50)
        
        # Test individual endpoints
        endpoints = [
            ("/api/health", "GET"),
            ("/api/dashboard", "GET"),
            ("/api/tickets", "GET"),
            ("/api/videos", "GET"),
        ]
        
        for endpoint, method in endpoints:
            logger.info(f"Testing {method} {endpoint}...")
            results[endpoint] = await self.benchmark.benchmark_endpoint(
                endpoint, method, iterations=100
            )
        
        # Generate report
        report = self.benchmark.generate_report()
        
        return {
            'results': results,
            'report': report,
            'system_metrics': self.benchmark.get_system_metrics()
        }

# Example usage
async def main():
    """Run performance tests."""
    runner = LoadTestRunner()
    results = await runner.run_full_load_test()
    
    print(results['report'])
    
    # Save results to file
    with open('performance_results.json', 'w') as f:
        import json
        json.dump(results, f, indent=2, default=str)

if __name__ == "__main__":
    asyncio.run(main())
