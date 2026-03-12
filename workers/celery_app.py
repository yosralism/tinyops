"""Celery application instance for tinyops."""

from __future__ import annotations

from celery import Celery

from workers.celery_config import CeleryConfig

# Create Celery instance
celery_app = Celery("tinyops")

# Load configuration from CeleryConfig class
celery_app.config_from_object(CeleryConfig)

# Auto-discover tasks in workers.tasks module
celery_app.autodiscover_tasks(["workers.tasks"])


@celery_app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task to test Celery is working."""
    print(f"Request: {self.request!r}")
    return "Celery is working!"
