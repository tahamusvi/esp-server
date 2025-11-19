from .base import *

CELERY_BROKER_URL = RABBIT_URI
CELERY_RESULT_BACKEND = REDIS_LINK
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

from celery.schedules import crontab

CELERY_TIMEZONE = "Europe/Amsterdam"
CELERY_ENABLE_UTC = True

CELERY_BEAT_SCHEDULE = {
    "enqueue-due-checks-every-minute": {
        "task": "monitor.tasks.enqueue_due_checks",
        "schedule": crontab(minute="*"),
    },
}