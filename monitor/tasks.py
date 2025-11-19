# monitor/tasks.py
from celery import shared_task
from django.utils import timezone
from zoneinfo import ZoneInfo
from datetime import timedelta, datetime
from croniter import croniter
from monitor.models import Check
from monitor.amqp import publish_check_request

def is_due_this_minute(cron_expr: str, now_local: datetime) -> bool:
    try:
        floor_now = now_local.replace(second=0, microsecond=0)
        base = floor_now - timedelta(minutes=1)
        return croniter(cron_expr, base).get_next(datetime) == floor_now
    except Exception:
        return False

@shared_task
def enqueue_due_checks():
    now_utc = timezone.now()
    for chk in Check.objects.filter(is_enabled=True).select_related("project"):
        tzname = chk.project.timezone or "Europe/Amsterdam"
        try:
            now_local = now_utc.astimezone(ZoneInfo(tzname))
        except Exception:
            now_local = now_utc

        if not is_due_this_minute(chk.schedule, now_local):
            continue

        publish_check_request(
            chk.project,
            chk,
            timeout_sec=chk.config.get("timeout", 10),
        )
