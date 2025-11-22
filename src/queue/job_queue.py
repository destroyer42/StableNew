"""In-memory job queue with simple priority + FIFO behavior."""

from __future__ import annotations

import heapq
from threading import Lock
from typing import Dict, List, Optional

from src.queue.job_model import Job, JobPriority, JobStatus


class JobQueue:
    """Thread-safe in-memory job queue."""

    def __init__(self) -> None:
        self._queue: list[tuple[int, int, str]] = []
        self._jobs: Dict[str, Job] = {}
        self._counter = 0
        self._lock = Lock()

    def submit(self, job: Job) -> None:
        with self._lock:
            self._counter += 1
            self._jobs[job.job_id] = job
            heapq.heappush(self._queue, (-int(job.priority), self._counter, job.job_id))

    def get_next_job(self) -> Optional[Job]:
        with self._lock:
            while self._queue:
                _, _, job_id = heapq.heappop(self._queue)
                job = self._jobs.get(job_id)
                if job and job.status == JobStatus.QUEUED:
                    return job
            return None

    def mark_running(self, job_id: str) -> None:
        self._update_status(job_id, JobStatus.RUNNING)

    def mark_completed(self, job_id: str, result: dict | None = None) -> None:
        job = self._update_status(job_id, JobStatus.COMPLETED)
        if job:
            job.result = result

    def mark_failed(self, job_id: str, error_message: str) -> None:
        job = self._update_status(job_id, JobStatus.FAILED, error_message)
        if job:
            job.error_message = error_message

    def list_jobs(self, status_filter: JobStatus | None = None) -> List[Job]:
        with self._lock:
            if status_filter is None:
                return list(self._jobs.values())
            return [job for job in self._jobs.values() if job.status == status_filter]

    def _update_status(self, job_id: str, status: JobStatus, error_message: str | None = None) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            job.mark_status(status, error_message)
            return job
