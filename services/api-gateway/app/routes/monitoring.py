"""
Monitoring routes for API Gateway
"""
from fastapi import APIRouter, HTTPException
import time
import psutil
from typing import Dict, Any, List
import asyncio

from shared.common.logging import get_logger

logger = get_logger("api-gateway")
router = APIRouter()

# Metrics storage (in production, use a proper metrics system)
metrics_store = {
    "requests_total": 0,
    "requests_by_service": {},
    "response_times": [],
    "errors_total": 0,
    "errors_by_service": {},
    "uptime_start": time.time()
}

@router.get("/metrics")
async def get_metrics():
    """Get gateway metrics in Prometheus format"""
    try:
        current_time = time.time()
        uptime = current_time - metrics_store["uptime_start"]

        metrics = f"""# API Gateway Metrics
# HELP gateway_requests_total Total number of requests processed
# TYPE gateway_requests_total counter
gateway_requests_total {metrics_store["requests_total"]}

# HELP gateway_errors_total Total number of errors
# TYPE gateway_errors_total counter
gateway_errors_total {metrics_store["errors_total"]}

# HELP gateway_uptime_seconds Gateway uptime in seconds
# TYPE gateway_uptime_seconds gauge
gateway_uptime_seconds {uptime}

# HELP gateway_services_total Total number of registered services
# TYPE gateway_services_total gauge
gateway_services_total 8

"""

        # Add per-service metrics
        for service, count in metrics_store["requests_by_service"].items():
            metrics += f"""# HELP gateway_requests_by_service_total Requests by service
# TYPE gateway_requests_by_service_total counter
gateway_requests_by_service_total{{service="{service}"}} {count}
"""

        for service, count in metrics_store["errors_by_service"].items():
            metrics += f"""# HELP gateway_errors_by_service_total Errors by service
# TYPE gateway_errors_by_service_total counter
gateway_errors_by_service_total{{service="{service}"}} {count}
"""

        return metrics

    except Exception as e:
        logger.error("Metrics retrieval failed", extra={"error": str(e)})
        raise HTTPException(500, "Metrics retrieval failed")

@router.get("/stats")
async def get_stats():
    """Get comprehensive gateway statistics"""
    try:
        current_time = time.time()
        uptime = current_time - metrics_store["uptime_start"]

        # Calculate response time statistics
        response_times = metrics_store["response_times"]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        min_response_time = min(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0

        stats = {
            "gateway": {
                "version": "1.0.0",
                "uptime_seconds": round(uptime, 2),
                "uptime_human": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m {int(uptime % 60)}s"
            },
            "requests": {
                "total": metrics_store["requests_total"],
                "by_service": metrics_store["requests_by_service"],
                "average_per_minute": round(metrics_store["requests_total"] / max(uptime / 60, 1), 2)
            },
            "performance": {
                "avg_response_time": round(avg_response_time, 3),
                "min_response_time": round(min_response_time, 3),
                "max_response_time": round(max_response_time, 3),
                "response_time_samples": len(response_times)
            },
            "errors": {
                "total": metrics_store["errors_total"],
                "by_service": metrics_store["errors_by_service"],
                "error_rate": round((metrics_store["errors_total"] / max(metrics_store["requests_total"], 1)) * 100, 2)
            },
            "system": {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "memory_used_mb": round(psutil.virtual_memory().used / 1024 / 1024, 2),
                "memory_total_mb": round(psutil.virtual_memory().total / 1024 / 1024, 2)
            },
            "timestamp": current_time
        }

        return stats

    except Exception as e:
        logger.error("Stats retrieval failed", extra={"error": str(e)})
        raise HTTPException(500, "Stats retrieval failed")

@router.get("/logs/recent")
async def get_recent_logs(lines: int = 50):
    """Get recent application logs"""
    try:
        # In production, this would read from a log file or logging system
        # For now, return a placeholder
        return {
            "logs": [
                {
                    "timestamp": time.time(),
                    "level": "INFO",
                    "message": "Gateway started successfully",
                    "service": "api-gateway"
                }
            ],
            "total_lines": 1,
            "requested_lines": lines
        }

    except Exception as e:
        logger.error("Log retrieval failed", extra={"error": str(e)})
        raise HTTPException(500, "Log retrieval failed")

@router.get("/performance")
async def get_performance_metrics():
    """Get detailed performance metrics"""
    try:
        response_times = metrics_store["response_times"]

        # Calculate percentiles
        if response_times:
            sorted_times = sorted(response_times)
            p50 = sorted_times[int(len(sorted_times) * 0.5)]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]
        else:
            p50 = p95 = p99 = 0

        performance = {
            "response_times": {
                "average": round(sum(response_times) / len(response_times), 3) if response_times else 0,
                "median": round(p50, 3),
                "95th_percentile": round(p95, 3),
                "99th_percentile": round(p99, 3),
                "min": round(min(response_times), 3) if response_times else 0,
                "max": round(max(response_times), 3) if response_times else 0
            },
            "throughput": {
                "requests_per_second": round(metrics_store["requests_total"] / max(time.time() - metrics_store["uptime_start"], 1), 2),
                "requests_per_minute": round(metrics_store["requests_total"] / max((time.time() - metrics_store["uptime_start"]) / 60, 1), 2)
            },
            "error_rates": {
                "overall": round((metrics_store["errors_total"] / max(metrics_store["requests_total"], 1)) * 100, 2),
                "by_service": {
                    service: round((count / max(metrics_store["requests_by_service"].get(service, 1), 1)) * 100, 2)
                    for service, count in metrics_store["errors_by_service"].items()
                }
            },
            "system_resources": {
                "cpu_usage_percent": psutil.cpu_percent(),
                "memory_usage_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent,
                "network_connections": len(psutil.net_connections())
            },
            "timestamp": time.time()
        }

        return performance

    except Exception as e:
        logger.error("Performance metrics retrieval failed", extra={"error": str(e)})
        raise HTTPException(500, "Performance metrics retrieval failed")

@router.get("/alerts")
async def get_alerts():
    """Get active alerts and warnings"""
    try:
        alerts = []
        current_time = time.time()

        # Check for high error rates
        error_rate = (metrics_store["errors_total"] / max(metrics_store["requests_total"], 1)) * 100
        if error_rate > 5:
            alerts.append({
                "id": "high_error_rate",
                "severity": "critical",
                "message": f"High error rate: {error_rate:.1f}%",
                "timestamp": current_time
            })

        # Check for high response times
        response_times = metrics_store["response_times"]
        if response_times:
            avg_response_time = sum(response_times) / len(response_times)
            if avg_response_time > 2.0:  # 2 seconds
                alerts.append({
                    "id": "high_response_time",
                    "severity": "warning",
                    "message": f"High average response time: {avg_response_time:.2f}s",
                    "timestamp": current_time
                })

        # Check system resources
        memory_percent = psutil.virtual_memory().percent
        if memory_percent > 90:
            alerts.append({
                "id": "high_memory_usage",
                "severity": "warning",
                "message": f"High memory usage: {memory_percent:.1f}%",
                "timestamp": current_time
            })

        cpu_percent = psutil.cpu_percent()
        if cpu_percent > 90:
            alerts.append({
                "id": "high_cpu_usage",
                "severity": "warning",
                "message": f"High CPU usage: {cpu_percent:.1f}%",
                "timestamp": current_time
            })

        return {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "timestamp": current_time
        }

    except Exception as e:
        logger.error("Alerts retrieval failed", extra={"error": str(e)})
        raise HTTPException(500, "Alerts retrieval failed")

@router.post("/metrics/reset")
async def reset_metrics():
    """Reset all metrics (admin only)"""
    try:
        # In production, this would require authentication
        global metrics_store
        metrics_store = {
            "requests_total": 0,
            "requests_by_service": {},
            "response_times": [],
            "errors_total": 0,
            "errors_by_service": {},
            "uptime_start": time.time()
        }

        logger.info("Metrics reset", extra={"timestamp": time.time()})

        return {"status": "metrics_reset", "timestamp": time.time()}

    except Exception as e:
        logger.error("Metrics reset failed", extra={"error": str(e)})
        raise HTTPException(500, "Metrics reset failed")

@router.get("/dashboard")
async def get_dashboard_data():
    """Get dashboard data for monitoring UI"""
    try:
        current_time = time.time()
        uptime = current_time - metrics_store["uptime_start"]

        dashboard = {
            "summary": {
                "uptime": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
                "total_requests": metrics_store["requests_total"],
                "error_rate": round((metrics_store["errors_total"] / max(metrics_store["requests_total"], 1)) * 100, 2),
                "avg_response_time": round(sum(metrics_store["response_times"]) / max(len(metrics_store["response_times"]), 1), 3)
            },
            "charts": {
                "requests_over_time": [],  # Would contain time-series data
                "errors_over_time": [],    # Would contain time-series data
                "response_times_over_time": []  # Would contain time-series data
            },
            "services": {
                service: {
                    "requests": count,
                    "errors": metrics_store["errors_by_service"].get(service, 0),
                    "error_rate": round((metrics_store["errors_by_service"].get(service, 0) / max(count, 1)) * 100, 2)
                }
                for service, count in metrics_store["requests_by_service"].items()
            },
            "system": {
                "cpu": psutil.cpu_percent(),
                "memory": psutil.virtual_memory().percent,
                "disk": psutil.disk_usage('/').percent
            },
            "timestamp": current_time
        }

        return dashboard

    except Exception as e:
        logger.error("Dashboard data retrieval failed", extra={"error": str(e)})
        raise HTTPException(500, "Dashboard data retrieval failed")

# Helper functions for metrics collection (would be called from middleware)
def record_request(service: str, response_time: float, status_code: int):
    """Record a request in metrics"""
    metrics_store["requests_total"] += 1

    if service not in metrics_store["requests_by_service"]:
        metrics_store["requests_by_service"][service] = 0
    metrics_store["requests_by_service"][service] += 1

    metrics_store["response_times"].append(response_time)

    # Keep only last 1000 response times
    if len(metrics_store["response_times"]) > 1000:
        metrics_store["response_times"] = metrics_store["response_times"][-1000:]

    # Record errors
    if status_code >= 400:
        metrics_store["errors_total"] += 1
        if service not in metrics_store["errors_by_service"]:
            metrics_store["errors_by_service"][service] = 0
        metrics_store["errors_by_service"][service] += 1

# Export the record function for use in other modules
__all__ = ["record_request"]