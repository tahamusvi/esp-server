from .base import *

WATCHDOG_AMQP = {
    "exchange_name": "watchdog.checks",
    "exchange_type": "direct",
    "request_queue": "watchdog.checks.requests",
    "result_queue":  "watchdog.checks.results",
    "routing_key_requests": "checks.run",
    "routing_key_results":  "checks.result",
}