"""Celery configuration for tinyops."""

from __future__ import annotations

from kombu import Exchange, Queue


class CeleryConfig:
    """Celery configuration class."""
    
    # Broker and Backend
    broker_url = "redis://localhost:6379/0"
    result_backend = "redis://localhost:6379/1"
    
    # Serialization
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]
    
    # Timezone
    timezone = "UTC"
    enable_utc = True
    
    # Task execution
    task_track_started = True
    task_time_limit = 3600  # 1 hour hard limit
    task_soft_time_limit = 3300  # 55 minutes soft limit
    task_acks_late = True
    task_reject_on_worker_lost = True
    
    # Worker
    worker_prefetch_multiplier = 1
    worker_max_tasks_per_child = 1000
    worker_disable_rate_limits = False
    
    # Results
    result_expires = 86400  # 24 hours
    result_persistent = True
    
    # Retries
    task_default_retry_delay = 60  # 1 minute
    task_max_retries = 3
    
    # Task routes - can customize per task
    task_routes = {
        "workers.tasks.device_tasks.*": {"queue": "devices"},
        "workers.tasks.monitoring.*": {"queue": "monitoring"},
    }
    
    # Queues
    task_queues = (
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("devices", Exchange("devices"), routing_key="devices"),
        Queue("monitoring", Exchange("monitoring"), routing_key="monitoring"),
    )
    
    task_default_queue = "default"
    task_default_exchange = "default"
    task_default_routing_key = "default"
    
    # Beat schedule (periodic tasks) - will be populated later
    beat_schedule = {}
