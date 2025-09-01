"""
Advanced monitoring and metrics system for LMS microservices
"""
import asyncio
import time
import psutil
import json
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from fastapi import Request, Response
from shared.common.logging import get_logger
from shared.common.cache import cache_manager

logger = get_logger("common-monitoring")


class MetricsCollector:
    """Advanced metrics collector"""

    def __init__(self):
        self.metrics: Dict[str, Any] = defaultdict(dict)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, Any]] = None):
        """Increment a counter metric"""
        async with self._lock:
            key = self._make_key(name, tags)
            self.counters[key] += value

    async def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, Any]] = None):
        """Set a gauge metric"""
        async with self._lock:
            key = self._make_key(name, tags)
            self.gauges[key] = value

    async def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, Any]] = None):
        """Record a histogram value"""
        async with self._lock:
            key = self._make_key(name, tags)
            self.histograms[key].append(value)

            # Keep only last 1000 values
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]

    async def record_timer(self, name: str, duration: float, tags: Optional[Dict[str, Any]] = None):
        """Record a timer duration"""
        await self.record_histogram(name, duration, tags)

    def _make_key(self, name: str, tags: Optional[Dict[str, Any]] = None) -> str:
        """Create a unique key for metric with tags"""
        if not tags:
            return name

        tag_str = ",".join([f"{k}={v}" for k, v in sorted(tags.items())])
        return f"{name}{{tag_str}}"

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics"""
        async with self._lock:
            summary = {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "histograms": {
                    name: {
                        "count": len(values),
                        "min": min(values) if values else 0,
                        "max": max(values) if values else 0,
                        "avg": sum(values) / len(values) if values else 0,
                        "p95": self._percentile(values, 95) if values else 0,
                        "p99": self._percentile(values, 99) if values else 0
                    }
                    for name, values in self.histograms.items()
                },
                "timers": {
                    name: {
                        "count": len(values),
                        "avg": sum(values) / len(values) if values else 0,
                        "p95": self._percentile(values, 95) if values else 0,
                        "p99": self._percentile(values, 99) if values else 0
                    }
                    for name, values in self.timers.items()
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            return summary

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile from list of values"""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


class HealthChecker:
    """Advanced health checker for services and dependencies"""

    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_results: Dict[str, Dict[str, Any]] = {}
        self.check_intervals: Dict[str, int] = {}

    def add_check(self, name: str, check_func: Callable, interval_seconds: int = 30):
        """Add a health check"""
        self.checks[name] = check_func
        self.check_intervals[name] = interval_seconds
        logger.info(f"Added health check: {name}")

    async def run_check(self, name: str) -> Dict[str, Any]:
        """Run a specific health check"""
        if name not in self.checks:
            return {"status": "error", "message": f"Check {name} not found"}

        try:
            start_time = time.time()
            result = await self.checks[name]()
            duration = time.time() - start_time

            health_result = {
                "status": result.get("status", "unknown"),
                "message": result.get("message", ""),
                "duration": round(duration, 3),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": result.get("details", {})
            }

            self.last_results[name] = health_result
            return health_result

        except Exception as e:
            error_result = {
                "status": "error",
                "message": str(e),
                "duration": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": {}
            }
            self.last_results[name] = error_result
            return error_result

    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = {}
        overall_status = "healthy"

        for name in self.checks.keys():
            result = await self.run_check(name)
            results[name] = result

            if result["status"] in ["error", "unhealthy"]:
                overall_status = "unhealthy"
            elif result["status"] == "degraded" and overall_status == "healthy":
                overall_status = "degraded"

        return {
            "overall_status": overall_status,
            "checks": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def get_check_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the last result of a health check"""
        return self.last_results.get(name)


class PerformanceMonitor:
    """Performance monitoring for requests and operations"""

    def __init__(self):
        self.request_times: deque = deque(maxlen=1000)
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "total_time": 0,
            "avg_time": 0,
            "min_time": float('inf'),
            "max_time": 0,
            "errors": 0,
            "last_request": None
        })

    async def record_request(
        self,
        endpoint: str,
        method: str,
        duration: float,
        status_code: int,
        user_id: Optional[str] = None
    ):
        """Record request performance metrics"""
        self.request_times.append(duration)

        stats = self.endpoint_stats[endpoint]
        stats["count"] += 1
        stats["total_time"] += duration
        stats["avg_time"] = stats["total_time"] / stats["count"]
        stats["min_time"] = min(stats["min_time"], duration)
        stats["max_time"] = max(stats["max_time"], duration)
        stats["last_request"] = datetime.now(timezone.utc).isoformat()

        if status_code >= 400:
            stats["errors"] += 1

        # Record metrics
        await metrics_collector.record_timer(
            "request_duration",
            duration,
            {"endpoint": endpoint, "method": method, "status": status_code}
        )

        await metrics_collector.increment_counter(
            "requests_total",
            tags={"endpoint": endpoint, "method": method, "status": status_code}
        )

    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if not self.request_times:
            return {"message": "No requests recorded yet"}

        sorted_times = sorted(self.request_times)

        return {
            "overall": {
                "total_requests": len(self.request_times),
                "avg_response_time": sum(self.request_times) / len(self.request_times),
                "min_response_time": min(self.request_times),
                "max_response_time": max(self.request_times),
                "p50_response_time": sorted_times[len(sorted_times) // 2],
                "p95_response_time": sorted_times[int(len(sorted_times) * 0.95)],
                "p99_response_time": sorted_times[int(len(sorted_times) * 0.99)]
            },
            "endpoints": dict(self.endpoint_stats),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class SystemMonitor:
    """System resource monitoring"""

    def __init__(self):
        self.last_cpu_percent = 0
        self.last_network_stats = {}

    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system resource statistics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_stats = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used
            }

            # Disk usage
            disk = psutil.disk_usage('/')
            disk_stats = {
                "total": disk.total,
                "free": disk.free,
                "used": disk.used,
                "percent": disk.percent
            }

            # Network I/O
            network = psutil.net_io_counters()
            network_stats = {
                "bytes_sent": network.bytes_sent,
                "bytes_recv": network.bytes_recv,
                "packets_sent": network.packets_sent,
                "packets_recv": network.packets_recv
            }

            return {
                "cpu_percent": cpu_percent,
                "memory": memory_stats,
                "disk": disk_stats,
                "network": network_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error("Failed to get system stats", extra={"error": str(e)})
            return {"error": str(e)}

    async def get_process_stats(self) -> Dict[str, Any]:
        """Get current process statistics"""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_times = process.cpu_times()

            return {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(),
                "memory_rss": memory_info.rss,
                "memory_vms": memory_info.vms,
                "cpu_user": cpu_times.user,
                "cpu_system": cpu_times.system,
                "num_threads": process.num_threads(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error("Failed to get process stats", extra={"error": str(e)})
            return {"error": str(e)}


# Global instances
metrics_collector = MetricsCollector()
health_checker = HealthChecker()
performance_monitor = PerformanceMonitor()
system_monitor = SystemMonitor()


# Middleware for request monitoring
@asynccontextmanager
async def monitor_request(request: Request, response: Optional[Response] = None):
    """Context manager for monitoring requests"""
    start_time = time.time()

    try:
        yield
    finally:
        duration = time.time() - start_time

        endpoint = request.url.path
        method = request.method
        status_code = response.status_code if response else 500

        # Extract user ID if available
        user_id = getattr(request.state, 'user_id', None) if hasattr(request, 'state') else None

        await performance_monitor.record_request(
            endpoint=endpoint,
            method=method,
            duration=duration,
            status_code=status_code,
            user_id=user_id
        )


# Default health checks
async def database_health_check():
    """Check database connectivity"""
    try:
        from shared.common.database import get_database
        db = await get_database()
        # Simple ping
        await db.command("ping")
        return {"status": "healthy", "message": "Database connection OK"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Database error: {str(e)}"}


async def redis_health_check():
    """Check Redis connectivity"""
    try:
        pong = await cache_manager.redis.get("health_check")
        return {"status": "healthy", "message": "Redis connection OK"}
    except Exception as e:
        return {"status": "unhealthy", "message": f"Redis error: {str(e)}"}


async def system_health_check():
    """Check system resources"""
    try:
        stats = await system_monitor.get_system_stats()

        # Check thresholds
        if stats["cpu_percent"] > 90:
            return {"status": "degraded", "message": "High CPU usage", "details": stats}
        elif stats["memory"]["percent"] > 90:
            return {"status": "degraded", "message": "High memory usage", "details": stats}
        else:
            return {"status": "healthy", "message": "System resources OK", "details": stats}
    except Exception as e:
        return {"status": "error", "message": f"System check failed: {str(e)}"}


# Register default health checks
health_checker.add_check("database", database_health_check)
health_checker.add_check("redis", redis_health_check)
health_checker.add_check("system", system_health_check)


# Monitoring API endpoints
async def get_monitoring_dashboard() -> Dict[str, Any]:
    """Get comprehensive monitoring dashboard data"""
    try:
        health_status = await health_checker.run_all_checks()
        performance_stats = await performance_monitor.get_performance_stats()
        system_stats = await system_monitor.get_system_stats()
        process_stats = await system_monitor.get_process_stats()
        metrics_summary = await metrics_collector.get_metrics_summary()
        cache_stats = await cache_manager.get_stats()

        return {
            "health": health_status,
            "performance": performance_stats,
            "system": system_stats,
            "process": process_stats,
            "metrics": metrics_summary,
            "cache": cache_stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error("Failed to get monitoring dashboard", extra={"error": str(e)})
        return {"error": str(e)}


async def get_health_status() -> Dict[str, Any]:
    """Get overall health status"""
    return await health_checker.run_all_checks()


async def get_metrics() -> Dict[str, Any]:
    """Get metrics summary"""
    return await metrics_collector.get_metrics_summary()


async def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics"""
    return await performance_monitor.get_performance_stats()


# Alerting system (basic)
class AlertManager:
    """Simple alerting system"""

    def __init__(self):
        self.alerts: List[Dict[str, Any]] = []
        self.thresholds: Dict[str, Dict[str, Any]] = {}

    def set_threshold(self, metric: str, threshold: Dict[str, Any]):
        """Set alert threshold for a metric"""
        self.thresholds[metric] = threshold

    async def check_thresholds(self):
        """Check all thresholds and generate alerts"""
        # This would be called periodically
        pass

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get current alerts"""
        return self.alerts


alert_manager = AlertManager()


# Background monitoring task
async def start_monitoring_tasks():
    """Start background monitoring tasks"""
    async def monitoring_loop():
        while True:
            try:
                # Update system metrics
                system_stats = await system_monitor.get_system_stats()
                await metrics_collector.set_gauge("cpu_usage", system_stats["cpu_percent"])
                await metrics_collector.set_gauge("memory_usage", system_stats["memory"]["percent"])
                await metrics_collector.set_gauge("disk_usage", system_stats["disk"]["percent"])

                # Update cache metrics
                cache_stats = await cache_manager.get_stats()
                await metrics_collector.set_gauge("cache_hit_rate", cache_stats.get("hit_rate", 0))

                await asyncio.sleep(60)  # Update every minute

            except Exception as e:
                logger.error("Error in monitoring loop", extra={"error": str(e)})
                await asyncio.sleep(60)

    # Start monitoring loop
    asyncio.create_task(monitoring_loop())
    logger.info("Started background monitoring tasks")