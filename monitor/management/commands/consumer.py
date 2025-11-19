# monitor/management/commands/consume_results.py
import json
import socket
import time
from datetime import datetime, timedelta, timezone as py_tz

from django.core.management.base import BaseCommand
from django.db import transaction
from django.core.cache import cache

from kombu import Consumer
from kombu.exceptions import OperationalError

from monitor.amqp import _conn, _exchange, _queues
from monitor.models import Project, Check, CheckRun, Incident


def parse_iso8601_z(s: str) -> datetime:
    if not s:
        return datetime.now(py_tz.utc)
    s = s.replace("Z", "+00:00")
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=py_tz.utc)
    return dt.astimezone(py_tz.utc)


class Command(BaseCommand):
    help = "Consume check results from RabbitMQ and persist as CheckRun."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Listening to results..."))

        # حلقهٔ بی‌نهایت برای ریکانکت
        while True:
            try:
                # هر بار کانکشن جدید بگیر تا اگر قبلی drop شد، باز بسازد
                with _conn() as conn:
                    ex = _exchange()
                    _, res_q = _queues(ex)

                    # صف را به کانکشن bind و declare کن (بعد از هر ریکانکت لازم است)
                    res_q.maybe_bind(conn)
                    res_q.declare()

                    # ساخت consumer
                    def on_message(body, message):
                        try:
                            # بدنه را اگر json نبود، خودمان parse کنیم
                            if isinstance(body, (bytes, bytearray)):
                                body = body.decode("utf-8", errors="replace")
                            if isinstance(body, str):
                                try:
                                    body = json.loads(body)
                                except json.JSONDecodeError:
                                    self.stderr.write(
                                        f"[consume_results] non-JSON string body received; content_type={getattr(message, 'content_type', None)}"
                                    )
                                    message.reject(requeue=False)
                                    return

                            if not isinstance(body, dict):
                                self.stderr.write(
                                    f"[consume_results] unexpected body type: {type(body)}; content_type={getattr(message, 'content_type', None)}"
                                )
                                message.reject(requeue=False)
                                return

                            props = getattr(message, "properties", {}) or {}
                            corr = body.get("correlation_id") or props.get("correlation_id")
                            if corr:
                                body["correlation_id"] = corr

                            self.stdout.write(f"[consume_results] received correlation_id={corr}")
                            self.process(body)
                            message.ack()

                        except Exception as e:
                            self.stderr.write(f"[consume_results] Error: {e}")
                            # اگر مشکل قابل تکرار است، requeue=False تا loop نشود
                            message.reject(requeue=False)

                    with Consumer(
                        conn,
                        queues=[res_q],
                        callbacks=[on_message],
                        # اجازه بده raw بیاد؛ خودمان parse می‌کنیم
                        accept=["json", "application/json"],
                        prefetch_count=50,
                    ) as consumer:
                        # event loop پایدار با heartbeat و timeout
                        while True:
                            try:
                                conn.drain_events(timeout=30)
                                # اگر timeout نشد هم گاهی heartbeat را چک کن
                                conn.heartbeat_check()
                            except socket.timeout:
                                # تایم‌اوت طبیعی؛ heartbeat را چک کن و ادامه بده
                                try:
                                    conn.heartbeat_check()
                                except Exception:
                                    raise  # تا بره تو ریکانکت
                                continue
                            except (OperationalError,) as e:
                                # خطای ارتباطی؛ بپر بیرون تا بیرون حلقه ریکانکت کند
                                self.stderr.write(f"[consume_results] connection lost: {e}; reconnecting...")
                                break

            except Exception as e:
                # خطا در ساخت کانکشن/مصرف؛ کمی صبر و دوباره
                self.stderr.write(f"[consume_results] outer loop error: {e}; retrying in 3s...")
                time.sleep(3)

    @transaction.atomic
    def process(self, body: dict):
        # --- idempotency ---
        corr = body.get("correlation_id")
        if not corr:
            raise ValueError("Missing correlation_id")
        if not cache.add(f"watchdog:processed:{corr}", "1", timeout=86400):
            return

        # --- Resolve ---
        project_id = body.get("project_id")
        check_id   = body.get("check_id")
        if not project_id or not check_id:
            raise ValueError("Missing project_id or check_id")

        project = Project.objects.get(id=project_id)
        check   = Check.objects.get(id=check_id, project=project)

        # --- times ---
        finished_at = parse_iso8601_z(body.get("finished_at"))
        latency_ms = body.get("latency_ms")
        if isinstance(latency_ms, int) and latency_ms >= 0:
            started_at = finished_at - timedelta(milliseconds=latency_ms)
        else:
            started_at = finished_at

        # --- status ---
        status = (body.get("status") or "").lower()
        if status not in {"pass", "warn", "fail", "error"}:
            raise ValueError(f"Invalid status: {status}")

        # --- http status tolerant ---
        http_status = body.get("http_status_code")
        if not isinstance(http_status, int):
            hs = body.get("http_status")
            http_status = hs if isinstance(hs, int) else None

        run = CheckRun.objects.create(
            project=project,
            target_check=check,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            latency_ms=latency_ms if isinstance(latency_ms, int) else None,
            http_status_code=http_status,
            result=body.get("result") or {},
            error_message=(body.get("error_message") or "")[:2000],
        )

        # --- incidents ---
        if status in ("fail", "error"):
            incident = (Incident.objects
                        .filter(project=project, target_check=check, state=Incident.State.OPEN)
                        .order_by("-last_seen_at").first())
            if incident:
                incident.consecutive_failures += 1
                incident.last_seen_at = finished_at
                incident.save(update_fields=["consecutive_failures", "last_seen_at"])
            else:
                incident = Incident.objects.create(
                    project=project,
                    target_check=check,
                    title=f"{check.name} failing",
                    description=f"Auto-opened by run {run.id}",
                    consecutive_failures=1,
                    first_seen_at=finished_at,
                    last_seen_at=finished_at,
                )
            run.opened_incident = incident
            run.save(update_fields=["opened_incident"])
        elif status == "pass":
            incident = (Incident.objects
                        .filter(project=project, target_check=check, state=Incident.State.OPEN)
                        .order_by("-last_seen_at").first())
            if incident:
                incident.state = Incident.State.RESOLVED
                incident.last_seen_at = finished_at
                incident.save(update_fields=["state", "last_seen_at"])
