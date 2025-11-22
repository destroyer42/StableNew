from __future__ import annotations

from datetime import datetime

from src.queue.job_model import Job, JobPriority, JobStatus
from src.pipeline.pipeline_runner import PipelineConfig


def test_job_serialization_and_status_update():
    cfg = PipelineConfig(prompt="p", model="m", sampler="Euler", width=512, height=512, steps=20, cfg_scale=7.0)
    job = Job(job_id="job-1", pipeline_config=cfg, priority=JobPriority.HIGH, learning_enabled=True)
    assert job.status == JobStatus.QUEUED
    job.mark_status(JobStatus.RUNNING)
    assert job.status == JobStatus.RUNNING
    payload = job.to_dict()
    assert payload["job_id"] == "job-1"
    assert payload["status"] == JobStatus.RUNNING.value
    assert isinstance(datetime.fromisoformat(payload["created_at"]), datetime)
