import json
import os
from datetime import datetime, timezone

from celery import Celery
from redis import Redis

from .database import SessionLocal
from .reporting import snapshot

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
celery = Celery("stockpilot", broker=REDIS_URL, backend=REDIS_URL)
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    broker_connection_timeout=2,
    broker_connection_retry_on_startup=True,
    task_publish_retry=False,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_time_limit=60,
    beat_schedule={"inventory-report-every-minute": {"task": "stockpilot.refresh_report", "schedule": 60.0}},
)


def redis_client():
    return Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2)


@celery.task(name="stockpilot.refresh_report")
def refresh_report():
    with SessionLocal() as db:
        report = snapshot(db)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    redis_client().setex("stockpilot:inventory-report", 180, json.dumps(report))
    return report
