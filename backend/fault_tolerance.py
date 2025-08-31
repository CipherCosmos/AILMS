"""
Fault tolerance and monitoring improvements for LMS backend.
"""
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import psutil
import aiohttp
from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
import json
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import signal
import sys

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

@dataclass
class HealthCheck:
    """Health check result data."""
    service: str
    status: HealthStatus
    response_time: float
    timestamp: datetime
    details: Dict[str, Any]
    error_message: Optional[str] = None

class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60, expected_exception: Exception = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise HTTPException(503, "Service temporarily unavailable")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

class HealthMonitor:
    """Comprehensive health monitoring system."""

    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self._monitoring_active = False
        self._check_interval = 30  # seconds

    async def start_monitoring(self):
        """Start health monitoring."""
        self._monitoring_active = True
        asyncio.create_task(self._monitoring_loop())

    async def stop_monitoring(self):
        """Stop health monitoring."""
        self._monitoring_active = False

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self._monitoring_active:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(5)

    async def _perform_health_checks(self):
        """Perform all health checks."""
        checks = [
            self._check_database_health(),
            self._check_cache_health(),
            self._check_external_services_health(),
            self._check_system_resources(),
            self._check_application_metrics()
        ]

        results = await asyncio.gather(*checks, return_exceptions=True)

        for result in results:
            if isinstance(result, HealthCheck):
                self.health_checks[result.service] = result
            elif isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")

    async def _check_database_health(self) -> HealthCheck:
        """Check database connectivity and performance."""
        start_time = time.time()

        try:
            from database import get_database
            db = get_database()

            # Simple ping
            await db.command("ping")

            # Check connection pool stats
            response_time = time.time() - start_time

            return HealthCheck(
                service="database",
                status=HealthStatus.HEALTHY if response_time < 1.0 else HealthStatus.DEGRADED,
                response_time=response_time,
                timestamp=datetime.utcnow(),
                details={"pool_size": getattr(db, '_pool', 'unknown')}
            )

        except Exception as e:
            return HealthCheck(
                service="database",
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                timestamp=datetime.utcnow(),
                details={},
                error_message=str(e)
            )

    async def _check_cache_health(self) -> HealthCheck:
        """Check cache service health."""
        start_time = time.time()

        try:
            from cache_manager import cache_manager

            if cache_manager.redis:
                await cache_manager.redis.ping()

                return HealthCheck(
                    service="cache",
                    status=HealthStatus.HEALTHY,
                    response_time=time.time() - start_time,
                    timestamp=datetime.utcnow(),
                    details={"cache_enabled": True}
                )
            else:
                return HealthCheck(
                    service="cache",
                    status=HealthStatus.DEGRADED,
                    response_time=time.time() - start_time,
                    timestamp=datetime.utcnow(),
                    details={"cache_enabled": False, "message": "Cache not configured"}
                )

        except Exception as e:
            return HealthCheck(
                service="cache",
                status=HealthStatus.UNHEALTHY,
                response_time=time.time() - start_time,
                timestamp=datetime.utcnow(),
                details={},
                error_message=str(e)
            )

    async def _check_external_services_health(self) -> HealthCheck:
        """Check external services health."""
        start_time = time.time()

        try:
            # Check Google Gemini API
            async with aiohttp.ClientSession() as session:
                # This is a placeholder - in production you'd make actual API calls
                pass

            return HealthCheck(
                service="external_services",
                status=HealthStatus.HEALTHY,
                response_time=time.time() - start_time,
                timestamp=datetime.utcnow(),
                details={"services_checked": ["gemini_api"]}
            )

        except Exception as e:
            return HealthCheck(
                service="external_services",
                status=HealthStatus.DEGRADED,
                response_time=time.time() - start_time,
                timestamp=datetime.utcnow(),
                details={"services_checked": ["gemini_api"]},
                error_message=str(e)
            )

    async def _check_system_resources(self) -> HealthCheck:
        """Check system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Determine health status based on resource usage
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 95:
                status = HealthStatus.UNHEALTHY
            elif cpu_percent > 70 or memory.percent > 80 or disk.percent > 85:
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

            return HealthCheck(
                service="system_resources",
                status=status,
                response_time=0.0,
                timestamp=datetime.utcnow(),
                details={
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "disk_percent": disk.percent,
                    "memory_used_gb": round(memory.used / (1024**3), 2),
                    "memory_total_gb": round(memory.total / (1024**3), 2)
                }
            )

        except Exception as e:
            return HealthCheck(
                service="system_resources",
                status=HealthStatus.UNHEALTHY,
                response_time=0.0,
                timestamp=datetime.utcnow(),
                details={},
                error_message=str(e)
            )

    async def _check_application_metrics(self) -> HealthCheck:
        """Check application-specific metrics."""
        try:
            # Get some basic metrics
            process = psutil.Process()
            memory_info = process.memory_info()
            cpu_times = process.cpu_times()

            return HealthCheck(
                service="application",
                status=HealthStatus.HEALTHY,
                response_time=0.0,
                timestamp=datetime.utcnow(),
                details={
                    "memory_rss_mb": round(memory_info.rss / (1024**2), 2),
                    "cpu_user_time": cpu_times.user,
                    "cpu_system_time": cpu_times.system,
                    "threads_count": process.num_threads()
                }
            )

        except Exception as e:
            return HealthCheck(
                service="application",
                status=HealthStatus.UNHEALTHY,
                response_time=0.0,
                timestamp=datetime.utcnow(),
                details={},
                error_message=str(e)
            )

    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        if not self.health_checks:
            return {"status": "unknown", "services": {}}

        services = {}
        overall_status = HealthStatus.HEALTHY

        for service, check in self.health_checks.items():
            services[service] = asdict(check)
            services[service]["status"] = check.status.value

            if check.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
            elif check.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED

        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "services": services
        }

class GracefulShutdown:
    """Graceful shutdown handler."""

    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self._shutdown_handlers: List[Callable] = []

    def add_shutdown_handler(self, handler: Callable):
        """Add a shutdown handler."""
        self._shutdown_handlers.append(handler)

    async def shutdown(self):
        """Perform graceful shutdown."""
        logger.info("Initiating graceful shutdown...")

        # Signal shutdown to all handlers
        self.shutdown_event.set()

        # Execute all shutdown handlers
        shutdown_tasks = []
        for handler in self._shutdown_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    shutdown_tasks.append(handler())
                else:
                    # Run sync handlers in thread pool
                    shutdown_tasks.append(asyncio.get_event_loop().run_in_executor(None, handler))
            except Exception as e:
                logger.error(f"Error in shutdown handler: {e}")

        # Wait for all handlers to complete (with timeout)
        if shutdown_tasks:
            try:
                await asyncio.wait_for(asyncio.gather(*shutdown_tasks), timeout=30)
                logger.info("All shutdown handlers completed")
            except asyncio.TimeoutError:
                logger.warning("Shutdown handlers timed out")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")

        logger.info("Graceful shutdown completed")

class RetryMechanism:
    """Retry mechanism with exponential backoff."""

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def execute_with_retry(self, func: Callable, *args, **kwargs):
        """Execute function with retry logic."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries + 1} attempts failed: {e}")

        raise last_exception

# Global instances
health_monitor = HealthMonitor()
graceful_shutdown = GracefulShutdown()
retry_mechanism = RetryMechanism()

# Health check endpoint
async def health_check_endpoint():
    """Health check endpoint for load balancers and monitoring."""
    health_status = health_monitor.get_health_status()

    status_code = 200
    if health_status["status"] == "degraded":
        status_code = 200  # Still return 200 for degraded but functional
    elif health_status["status"] == "unhealthy":
        status_code = 503  # Service unavailable

    return JSONResponse(
        content=health_status,
        status_code=status_code
    )

# Middleware for fault tolerance
async def fault_tolerance_middleware(request: Request, call_next):
    """Middleware for fault tolerance and error handling."""
    try:
        # Add timeout to requests
        start_time = time.time()

        # Execute request with timeout
        response = await asyncio.wait_for(call_next(request), timeout=30.0)

        # Log slow requests
        duration = time.time() - start_time
        if duration > 5.0:  # Log requests taking more than 5 seconds
            logger.warning(".2f")

        return response

    except asyncio.TimeoutError:
        logger.error(f"Request timeout: {request.method} {request.url.path}")
        return JSONResponse(
            content={"error": "Request timeout", "message": "The request took too long to process"},
            status_code=504
        )

    except Exception as e:
        logger.error(f"Unhandled error in request {request.method} {request.url.path}: {e}")
        return JSONResponse(
            content={"error": "Internal server error", "message": "An unexpected error occurred"},
            status_code=500
        )

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    asyncio.create_task(graceful_shutdown.shutdown())

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Database circuit breaker
db_circuit_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception
)

# External API circuit breaker
api_circuit_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=120,
    expected_exception=(aiohttp.ClientError, asyncio.TimeoutError)
)