import uuid
import logging
from datetime import datetime, timezone
from kombu import Connection, Exchange, Queue, Producer
from kombu.exceptions import OperationalError
from django.conf import settings
import json
from .utils import deep_merge, mask_secrets

log = logging.getLogger(__name__)


def publish_dict_check_request(project, check, timeout_sec: int = 10, *, overrides: dict | None = None, type_override: str | None = None) -> str:
    corr_id = str(uuid.uuid4())

    merged_cfg = deep_merge(check.config or {}, overrides or {})

    payload = {
        "version": 1,
        "correlation_id": corr_id,
        "project_id": str(project.id),
        "check_id": str(check.id),
        "type": type_override or check.type,
        "config": merged_cfg,  # ← مرج نهایی
        "timeout_sec": int(timeout_sec),
        "reply_to": settings.WATCHDOG_AMQP["result_queue"],
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        with _conn() as conn:
            channel = conn.channel()
            producer = Producer(channel)

            ex = _exchange()
            req_q, _ = _queues(ex)
            ex.declare(channel=channel)
            req_q.declare(channel=channel)

            undelivered = {"flag": False, "reason": None}
            def on_return(exception, exchange, routing_key, message):
                undelivered["flag"] = True
                undelivered["reason"] = f"Routing failed for key={routing_key}"

            producer.publish(
                payload,                      # ← dict خام
                exchange=ex,
                routing_key=settings.WATCHDOG_AMQP["routing_key_requests"],
                serializer="json",            # ← Kombu خودش dumps می‌کند و bytes می‌سازد
                delivery_mode=2,
                correlation_id=corr_id,
                reply_to=settings.WATCHDOG_AMQP["result_queue"],
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                mandatory=True,
                retry=True,
                retry_policy={"max_retries": 5, "interval_start": 0.2, "interval_step": 0.5, "interval_max": 2},
                declare=[req_q],
                on_return=on_return,
            )

            if undelivered["flag"]:
                log.warning("Message undeliverable: %s", undelivered["reason"])

        # لاگ بدون افشای secrets
        log.info(
            "Published check corr_id=%s project=%s check=%s type=%s overrides=%s",
            corr_id, project.id, check.id, payload["type"], mask_secrets(overrides or {}),
        )
        return corr_id

    except OperationalError as e:
        log.error("AMQP connection/publish error: %s | corr_id=%s", e, corr_id)
        raise


def _conn() -> Connection:
    return Connection(
        settings.RABBIT_URI,
        heartbeat=20,
        connect_timeout=5,
        transport_options={"confirm_publish": True},
    )

def _exchange() -> Exchange:
    cfg = settings.WATCHDOG_AMQP
    return Exchange(
        cfg["exchange_name"],
        type=cfg["exchange_type"],
        durable=True,
        delivery_mode=2,
    )

def _queues(ex: Exchange):
    cfg = settings.WATCHDOG_AMQP
    req = Queue(
        cfg["request_queue"],
        exchange=ex,
        routing_key=cfg["routing_key_requests"],
        durable=True,
    )
    res = Queue(
        cfg["result_queue"],
        exchange=ex,
        routing_key=cfg["routing_key_results"],
        durable=True,
    )
    return req, res


def publish_check_request(project, check, timeout_sec: int = 10) -> str:
    corr_id = str(uuid.uuid4())
    payload = {
        "version": 1,
        "correlation_id": corr_id,
        "project_id": str(project.id),
        "check_id": str(check.id),
        "type": check.type,
        "config": check.config or {},
        "timeout_sec": int(timeout_sec),
        "reply_to": settings.WATCHDOG_AMQP["result_queue"],
        "sent_at": datetime.now(timezone.utc).isoformat(),
    }

    with _conn() as conn:
        channel = conn.channel()
        producer = Producer(channel)

        ex = _exchange()
        req_q, _ = _queues(ex)
        ex.declare(channel=channel)
        req_q.declare(channel=channel)

        undelivered = {"flag": False, "reason": None}
        def on_return(exc, exchange, routing_key, message):
            undelivered["flag"] = True
            undelivered["reason"] = f"Routing failed for key={routing_key}"

        producer.publish(
            payload,                              # ← dict خام
            exchange=ex,
            routing_key=settings.WATCHDOG_AMQP["routing_key_requests"],
            serializer="json",                    # ← کومبو خودش به bytes تبدیل می‌کند
            delivery_mode=2,
            correlation_id=corr_id,
            reply_to=settings.WATCHDOG_AMQP["result_queue"],
            timestamp=int(datetime.now(timezone.utc).timestamp()),
            mandatory=True,
            retry=True,
            retry_policy={"max_retries": 5, "interval_start": 0.2, "interval_step": 0.5, "interval_max": 2},
            declare=[req_q],
            on_return=on_return,
        )

        if undelivered["flag"]:
            log.warning("Message undeliverable: %s", undelivered["reason"])

    log.info("Published check request corr_id=%s project=%s check=%s", corr_id, project.id, check.id)
    return corr_id

