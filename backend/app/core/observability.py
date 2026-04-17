from __future__ import annotations

import contextvars
import logging
import time
import uuid
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from prometheus_client import start_http_server as prometheus_start_http_server
from pythonjsonlogger.json import JsonFormatter

from app.core.config import settings

request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_id",
    default=None,
)

http_requests_total = Counter(
    "filesh_http_requests_total",
    "Total number of HTTP requests.",
    ["method", "path", "status_code"],
)
http_request_duration_seconds = Histogram(
    "filesh_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "path"],
)
cleanup_events_total = Counter(
    "filesh_cleanup_events_total",
    "Total number of cleanup worker events by outcome.",
    ["event_type", "topic", "outcome"],
)
cleanup_event_duration_seconds = Histogram(
    "filesh_cleanup_event_duration_seconds",
    "Cleanup worker processing latency in seconds.",
    ["event_type", "topic", "outcome"],
)
cleanup_consumer_lag_messages = Gauge(
    "filesh_cleanup_consumer_lag_messages",
    "Estimated cleanup consumer lag in messages.",
    ["topic", "partition", "group_id"],
)
cleanup_consumer_offset = Gauge(
    "filesh_cleanup_consumer_offset",
    "Observed cleanup consumer and end offsets.",
    ["topic", "partition", "group_id", "kind"],
)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if getattr(configure_logging, "_configured", False):
        root_logger.setLevel(settings.log_level.upper())
        return

    handler = logging.StreamHandler()
    if settings.log_json:
        handler.setFormatter(
            JsonFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
            )
        )
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s [request_id=%(request_id)s] %(message)s",
            )
        )
    handler.addFilter(RequestContextFilter())
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(settings.log_level.upper())
    configure_logging._configured = True


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


def get_request_id() -> str | None:
    return request_id_context.get()


def set_request_id(request_id: str | None) -> contextvars.Token[str | None]:
    return request_id_context.set(request_id)


def reset_request_id(token: contextvars.Token[str | None]) -> None:
    request_id_context.reset(token)


def get_or_create_request_id(request_id: str | None = None) -> str:
    return request_id or str(uuid.uuid4())


def observe_http_request(method: str, path: str, status_code: int, duration: float) -> None:
    if not settings.metrics_enabled:
        return
    labels = {"method": method, "path": path}
    http_requests_total.labels(status_code=str(status_code), **labels).inc()
    http_request_duration_seconds.labels(**labels).observe(duration)


def observe_cleanup_event(
    *,
    event_type: str,
    topic: str,
    outcome: str,
    duration: float,
) -> None:
    if not settings.metrics_enabled:
        return
    labels = {
        "event_type": event_type,
        "topic": topic,
        "outcome": outcome,
    }
    cleanup_events_total.labels(**labels).inc()
    cleanup_event_duration_seconds.labels(**labels).observe(duration)


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def start_metrics_server(port: int) -> None:
    if not settings.metrics_enabled:
        return
    prometheus_start_http_server(port)


def observe_cleanup_consumer_position(
    *,
    topic: str,
    partition: int,
    group_id: str,
    current_offset: int,
    end_offset: int,
) -> None:
    if not settings.metrics_enabled:
        return
    labels = {
        "topic": topic,
        "partition": str(partition),
        "group_id": group_id,
    }
    cleanup_consumer_offset.labels(kind="current", **labels).set(current_offset)
    cleanup_consumer_offset.labels(kind="end", **labels).set(end_offset)
    cleanup_consumer_lag_messages.labels(**labels).set(max(end_offset - current_offset, 0))


def request_log_extra(**extra: Any) -> dict[str, Any]:
    payload = dict(extra)
    if "request_id" not in payload:
        payload["request_id"] = get_request_id()
    return payload


def current_time() -> float:
    return time.perf_counter()
