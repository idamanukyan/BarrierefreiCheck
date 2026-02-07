"""
Job Queue Service

BullMQ-compatible job queue for scan processing.
"""

import json
import time
import logging
from typing import Any, Optional
from uuid import UUID

import redis
from app.config import settings

logger = logging.getLogger(__name__)

# Queue names - must match scanner/src/workers/queue.ts
SCAN_QUEUE = "accessibility-scans"

# Redis connection pool
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Get Redis client for queue operations."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _redis_client


def add_scan_job(
    scan_id: UUID,
    url: str,
    crawl: bool,
    max_pages: int,
    user_id: UUID,
    options: Optional[dict] = None,
) -> bool:
    """
    Add a scan job to the BullMQ queue.

    This function creates a job in the format expected by BullMQ.
    BullMQ stores jobs as Redis hashes and uses sorted sets for job ordering.
    """
    try:
        r = get_redis_client()
        job_id = str(scan_id)
        timestamp = int(time.time() * 1000)  # milliseconds

        # Job data structure matching ScanJobData in scanner
        job_data = {
            "scanId": job_id,
            "url": url,
            "crawl": crawl,
            "maxPages": max_pages,
            "userId": str(user_id),
            "options": options or {
                "captureScreenshots": True,
                "respectRobotsTxt": True,
            },
        }

        # BullMQ job options
        job_opts = {
            "jobId": job_id,
            "attempts": 3,
            "backoff": {
                "type": "exponential",
                "delay": 5000,
            },
            "timestamp": timestamp,
        }

        # BullMQ stores job data in a hash
        job_key = f"bull:{SCAN_QUEUE}:{job_id}"
        job_hash = {
            "name": f"scan-{job_id}",
            "data": json.dumps(job_data),
            "opts": json.dumps(job_opts),
            "timestamp": str(timestamp),
            "delay": "0",
            "priority": "0",
            "processedOn": "",
            "finishedOn": "",
            "returnvalue": "",
            "failedReason": "",
            "stacktrace": "[]",
            "attemptsMade": "0",
        }

        # Use a Redis pipeline for atomic operations
        pipe = r.pipeline()

        # Store job data hash
        pipe.hset(job_key, mapping=job_hash)

        # Add job ID to the waiting list
        # BullMQ uses a sorted set for priority queue
        pipe.zadd(f"bull:{SCAN_QUEUE}:wait", {job_id: timestamp})

        # Also add to the "id" set for tracking
        pipe.sadd(f"bull:{SCAN_QUEUE}:meta", "")

        # Execute pipeline
        pipe.execute()

        logger.info(f"Scan job {job_id} queued successfully for URL: {url}")
        return True

    except redis.RedisError as e:
        logger.error(f"Failed to queue scan job {scan_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error queuing scan job {scan_id}: {e}")
        return False


def get_job_status(scan_id: UUID) -> Optional[dict]:
    """Get the status of a job from the queue."""
    try:
        r = get_redis_client()
        job_id = str(scan_id)
        job_key = f"bull:{SCAN_QUEUE}:{job_id}"

        job_data = r.hgetall(job_key)
        if not job_data:
            return None

        return {
            "id": job_id,
            "name": job_data.get("name"),
            "attempts_made": int(job_data.get("attemptsMade", 0)),
            "processed_on": job_data.get("processedOn") or None,
            "finished_on": job_data.get("finishedOn") or None,
            "failed_reason": job_data.get("failedReason") or None,
        }

    except redis.RedisError as e:
        logger.error(f"Failed to get job status for {scan_id}: {e}")
        return None


def cancel_job(scan_id: UUID) -> bool:
    """Remove a job from the waiting queue."""
    try:
        r = get_redis_client()
        job_id = str(scan_id)

        # Remove from waiting queue
        removed = r.zrem(f"bull:{SCAN_QUEUE}:wait", job_id)

        if removed:
            logger.info(f"Job {job_id} removed from queue")
            return True
        else:
            logger.warning(f"Job {job_id} not found in waiting queue")
            return False

    except redis.RedisError as e:
        logger.error(f"Failed to cancel job {scan_id}: {e}")
        return False
