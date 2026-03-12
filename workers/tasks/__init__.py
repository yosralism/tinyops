"""Tasks package for Celery workers."""

from workers.tasks.device_tasks import collect_device_data, collect_multiple_devices

__all__ = ["collect_device_data", "collect_multiple_devices"]

