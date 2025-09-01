"""
Background job processing system for LMS microservices
"""
import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Callable, Awaitable
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
from enum import Enum
from dataclasses import dataclass, asdict
from shared.common.logging import get_logger
from shared.common.cache import cache_manager
from shared.common.monitoring import metrics_collector

logger = get_logger("common-jobs")


class JobStatus(Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class JobPriority(Enum):
    """Job priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Job:
    """Job data structure"""
    id: str
    name: str
    func_name: str
    args: List[Any]
    kwargs: Dict[str, Any]
    priority: JobPriority
    status: JobStatus
    created_at: datetime
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Any]
    error: Optional[str]
    retry_count: int
    max_retries: int
    timeout_seconds: Optional[int]
    progress: float = 0.0
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary"""
        data = asdict(self)
        # Convert enums to strings
        data["priority"] = self.priority.value
        data["status"] = self.status.value
        # Convert datetimes to ISO strings
        for field in ["created_at", "scheduled_at", "started_at", "completed_at"]:
            if getattr(self, field):
                data[field] = getattr(self, field).isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Job':
        """Create job from dictionary"""
        # Convert strings back to enums
        data["priority"] = JobPriority(data["priority"])
        data["status"] = JobStatus(data["status"])
        # Convert ISO strings back to datetimes
        for field in ["created_at", "scheduled_at", "started_at", "completed_at"]:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        return cls(**data)


class JobQueue:
    """Job queue with priority support"""

    def __init__(self):
        self.jobs: Dict[str, Job] = {}
        self.priority_queues: Dict[JobPriority, List[str]] = {
            priority: [] for priority in JobPriority
        }
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.completed_jobs: deque = deque(maxlen=1000)  # Keep last 1000 completed jobs
        self._lock = asyncio.Lock()

    async def enqueue(
        self,
        name: str,
        func: Callable,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        priority: JobPriority = JobPriority.NORMAL,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = 3,
        timeout_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add job to queue"""
        job_id = str(uuid.uuid4())

        job = Job(
            id=job_id,
            name=name,
            func_name=func.__name__,
            args=args or [],
            kwargs=kwargs or {},
            priority=priority,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            scheduled_at=scheduled_at,
            started_at=None,
            completed_at=None,
            result=None,
            error=None,
            retry_count=0,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            metadata=metadata or {}
        )

        async with self._lock:
            self.jobs[job_id] = job

            if scheduled_at and scheduled_at > datetime.now(timezone.utc):
                # Scheduled job - will be picked up by scheduler
                pass
            else:
                # Add to priority queue
                self.priority_queues[priority].append(job_id)

        # Store in cache for persistence
        await cache_manager.set(f"job:{job_id}", job.to_dict(), ttl=86400)  # 24 hours

        logger.info(f"Job enqueued: {name} ({job_id})")
        await metrics_collector.increment_counter("jobs_enqueued", tags={"priority": priority.value})

        return job_id

    async def dequeue(self) -> Optional[Job]:
        """Get next job from queue"""
        async with self._lock:
            # Check priority queues in order (highest first)
            for priority in [JobPriority.CRITICAL, JobPriority.HIGH, JobPriority.NORMAL, JobPriority.LOW]:
                if self.priority_queues[priority]:
                    job_id = self.priority_queues[priority].pop(0)
                    job = self.jobs.get(job_id)
                    if job and job.status == JobStatus.PENDING:
                        job.status = JobStatus.RUNNING
                        job.started_at = datetime.now(timezone.utc)
                        return job

        return None

    async def complete_job(self, job_id: str, result: Any = None):
        """Mark job as completed"""
        async with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                job.result = result
                job.progress = 100.0

                # Move to completed jobs
                self.completed_jobs.append(job.to_dict())

                # Remove from running jobs
                if job_id in self.running_jobs:
                    del self.running_jobs[job_id]

        # Update cache
        await cache_manager.set(f"job:{job_id}", job.to_dict(), ttl=86400)

        logger.info(f"Job completed: {job.name} ({job_id})")
        await metrics_collector.increment_counter("jobs_completed")

    async def fail_job(self, job_id: str, error: str):
        """Mark job as failed"""
        async with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)
                job.error = error

                # Check if should retry
                if job.retry_count < job.max_retries:
                    job.status = JobStatus.RETRY
                    job.retry_count += 1
                    # Re-queue with lower priority
                    retry_priority_value = max(1, job.priority.value - 1)
                    retry_priority = JobPriority(retry_priority_value)
                    self.priority_queues[retry_priority].append(job_id)
                    logger.info(f"Job scheduled for retry: {job.name} ({job_id}) - attempt {job.retry_count}")
                else:
                    # Move to completed jobs
                    self.completed_jobs.append(job.to_dict())

                # Remove from running jobs
                if job_id in self.running_jobs:
                    del self.running_jobs[job_id]

        # Update cache
        await cache_manager.set(f"job:{job_id}", job.to_dict(), ttl=86400)

        logger.error(f"Job failed: {job.name} ({job_id})", extra={"error": error})
        await metrics_collector.increment_counter("jobs_failed")

    async def cancel_job(self, job_id: str):
        """Cancel a job"""
        async with self._lock:
            if job_id in self.jobs:
                job = self.jobs[job_id]
                job.status = JobStatus.CANCELLED
                job.completed_at = datetime.now(timezone.utc)

                # Cancel running task
                if job_id in self.running_jobs:
                    self.running_jobs[job_id].cancel()
                    del self.running_jobs[job_id]

        # Update cache
        await cache_manager.set(f"job:{job_id}", job.to_dict(), ttl=86400)

        logger.info(f"Job cancelled: {job.name} ({job_id})")
        await metrics_collector.increment_counter("jobs_cancelled")

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status"""
        # Try cache first
        cached_job = await cache_manager.get(f"job:{job_id}")
        if cached_job:
            return cached_job

        # Try memory
        async with self._lock:
            job = self.jobs.get(job_id)
            if job:
                return job.to_dict()

        return None

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        async with self._lock:
            stats = {
                "total_jobs": len(self.jobs),
                "running_jobs": len(self.running_jobs),
                "completed_jobs": len(self.completed_jobs),
                "queue_lengths": {
                    priority.name: len(queue)
                    for priority, queue in self.priority_queues.items()
                }
            }

            # Count jobs by status
            status_counts = defaultdict(int)
            for job in self.jobs.values():
                status_counts[job.status.value] += 1

            stats["status_counts"] = dict(status_counts)
            return stats


class JobScheduler:
    """Job scheduler for delayed and recurring jobs"""

    def __init__(self, job_queue: JobQueue):
        self.job_queue = job_queue
        self.scheduled_jobs: Dict[str, Job] = {}
        self.recurring_jobs: Dict[str, Dict[str, Any]] = {}
        self._scheduler_task: Optional[asyncio.Task] = None

    async def schedule_job(
        self,
        name: str,
        func: Callable,
        run_at: datetime,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        priority: JobPriority = JobPriority.NORMAL
    ) -> str:
        """Schedule a job to run at specific time"""
        job_id = await self.job_queue.enqueue(
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            scheduled_at=run_at
        )

        self.scheduled_jobs[job_id] = self.job_queue.jobs[job_id]
        logger.info(f"Job scheduled: {name} at {run_at}")
        return job_id

    async def schedule_recurring(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        priority: JobPriority = JobPriority.NORMAL,
        max_runs: Optional[int] = None
    ) -> str:
        """Schedule a recurring job"""
        job_id = str(uuid.uuid4())

        self.recurring_jobs[job_id] = {
            "name": name,
            "func": func,
            "interval_seconds": interval_seconds,
            "args": args or [],
            "kwargs": kwargs or {},
            "priority": priority,
            "max_runs": max_runs,
            "run_count": 0,
            "next_run": datetime.now(timezone.utc) + timedelta(seconds=interval_seconds),
            "last_run": None
        }

        logger.info(f"Recurring job scheduled: {name} every {interval_seconds}s")
        return job_id

    async def start_scheduler(self):
        """Start the scheduler"""
        if self._scheduler_task is None:
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info("Job scheduler started")

    async def stop_scheduler(self):
        """Stop the scheduler"""
        if self._scheduler_task:
            self._scheduler_task.cancel()
            self._scheduler_task = None
            logger.info("Job scheduler stopped")

    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while True:
            try:
                now = datetime.now(timezone.utc)

                # Check scheduled jobs
                for job_id, job in list(self.scheduled_jobs.items()):
                    if job.scheduled_at and job.scheduled_at <= now:
                        # Move to regular queue
                        self.job_queue.priority_queues[job.priority].append(job_id)
                        del self.scheduled_jobs[job_id]
                        logger.info(f"Scheduled job moved to queue: {job.name} ({job_id})")

                # Check recurring jobs
                for job_id, recurring in list(self.recurring_jobs.items()):
                    if recurring["next_run"] <= now:
                        # Schedule next run
                        await self.job_queue.enqueue(
                            name=recurring["name"],
                            func=recurring["func"],
                            args=recurring["args"],
                            kwargs=recurring["kwargs"],
                            priority=recurring["priority"]
                        )

                        recurring["run_count"] += 1
                        recurring["last_run"] = now

                        # Check if max runs reached
                        if recurring["max_runs"] and recurring["run_count"] >= recurring["max_runs"]:
                            del self.recurring_jobs[job_id]
                            logger.info(f"Recurring job completed: {recurring['name']} ({job_id})")
                        else:
                            # Schedule next run
                            recurring["next_run"] = now + timedelta(seconds=recurring["interval_seconds"])

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error("Error in scheduler loop", extra={"error": str(e)})
                await asyncio.sleep(10)


class JobWorker:
    """Job worker that processes jobs from queue"""

    def __init__(self, job_queue: JobQueue, job_registry: Dict[str, Callable]):
        self.job_queue = job_queue
        self.job_registry = job_registry
        self.is_running = False
        self.workers: List[asyncio.Task] = []
        self.max_workers = 4

    async def start_workers(self, num_workers: int = 4):
        """Start job workers"""
        self.max_workers = num_workers
        self.is_running = True

        for i in range(num_workers):
            worker_task = asyncio.create_task(self._worker_loop(i))
            self.workers.append(worker_task)

        logger.info(f"Started {num_workers} job workers")

    async def stop_workers(self):
        """Stop all job workers"""
        self.is_running = False

        for worker in self.workers:
            worker.cancel()

        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

        logger.info("Job workers stopped")

    async def _worker_loop(self, worker_id: int):
        """Worker loop for processing jobs"""
        logger.info(f"Worker {worker_id} started")

        while self.is_running:
            try:
                # Get next job
                job = await self.job_queue.dequeue()

                if job:
                    # Execute job
                    await self._execute_job(job, worker_id)
                else:
                    # No jobs available, wait
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in worker {worker_id}", extra={"error": str(e)})
                await asyncio.sleep(1)

        logger.info(f"Worker {worker_id} stopped")

    async def _execute_job(self, job: Job, worker_id: int):
        """Execute a job"""
        logger.info(f"Worker {worker_id} executing job: {job.name} ({job.id})")

        # Store running job reference
        task = asyncio.current_task()
        if task:
            self.job_queue.running_jobs[job.id] = task

        try:
            # Get function from registry
            func = self.job_registry.get(job.func_name)
            if not func:
                raise ValueError(f"Function {job.func_name} not found in registry")

            # Execute with timeout if specified
            if job.timeout_seconds:
                result = await asyncio.wait_for(
                    func(*job.args, **job.kwargs),
                    timeout=job.timeout_seconds
                )
            else:
                result = await func(*job.args, **job.kwargs)

            # Mark as completed
            await self.job_queue.complete_job(job.id, result)

        except asyncio.TimeoutError:
            error = f"Job timed out after {job.timeout_seconds} seconds"
            await self.job_queue.fail_job(job.id, error)

        except Exception as e:
            error = f"Job execution failed: {str(e)}"
            await self.job_queue.fail_job(job.id, error)


# Global instances
job_queue = JobQueue()
job_scheduler = JobScheduler(job_queue)
job_worker = JobWorker(job_queue, {})

# Job registry - functions must be registered here
job_registry = job_worker.job_registry


def register_job(func: Callable) -> Callable:
    """Decorator to register a job function"""
    job_registry[func.__name__] = func
    return func


# Convenience functions
async def enqueue_job(
    name: str,
    func: Callable,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
    priority: JobPriority = JobPriority.NORMAL,
    scheduled_at: Optional[datetime] = None,
    max_retries: int = 3,
    timeout_seconds: Optional[int] = None
) -> str:
    """Enqueue a job"""
    return await job_queue.enqueue(
        name=name,
        func=func,
        args=args,
        kwargs=kwargs,
        priority=priority,
        scheduled_at=scheduled_at,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds
    )


async def schedule_job(
    name: str,
    func: Callable,
    run_at: datetime,
    args: Optional[List[Any] ] = None,
    kwargs: Optional[Dict[str, Any]] = None,
    priority: JobPriority = JobPriority.NORMAL
) -> str:
    """Schedule a job"""
    return await job_scheduler.schedule_job(
        name=name,
        func=func,
        run_at=run_at,
        args=args,
        kwargs=kwargs,
        priority=priority
    )


async def schedule_recurring_job(
    name: str,
    func: Callable,
    interval_seconds: int,
    args: Optional[List[Any]] = None,
    kwargs: Optional[Dict[str, Any]] = None,
    priority: JobPriority = JobPriority.NORMAL,
    max_runs: Optional[int] = None
) -> str:
    """Schedule a recurring job"""
    return await job_scheduler.schedule_recurring(
        name=name,
        func=func,
        interval_seconds=interval_seconds,
        args=args,
        kwargs=kwargs,
        priority=priority,
        max_runs=max_runs
    )


async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status"""
    return await job_queue.get_job_status(job_id)


async def cancel_job(job_id: str):
    """Cancel a job"""
    await job_queue.cancel_job(job_id)


async def get_job_stats() -> Dict[str, Any]:
    """Get job processing statistics"""
    queue_stats = await job_queue.get_queue_stats()

    # Add timing metrics
    await metrics_collector.set_gauge("jobs_queued", queue_stats["total_jobs"])
    await metrics_collector.set_gauge("jobs_running", queue_stats["running_jobs"])

    return queue_stats


# Background job processing startup
async def start_job_processing(num_workers: int = 4):
    """Start job processing system"""
    await job_scheduler.start_scheduler()
    await job_worker.start_workers(num_workers)
    logger.info("Job processing system started")


async def stop_job_processing():
    """Stop job processing system"""
    await job_scheduler.stop_scheduler()
    await job_worker.stop_workers()
    logger.info("Job processing system stopped")