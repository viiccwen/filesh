from __future__ import annotations

import logging

from opentelemetry import trace
from opentelemetry.context import attach, detach
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from app.core.events import build_cleanup_event
from app.core.observability import RequestContextFilter, get_or_create_request_id, request_log_extra
from app.core.tracing import TRACE_CONTEXT_METADATA_KEY
from tests_helpers import register_and_login


def test_healthcheck_echoes_request_id_header(client) -> None:
    response = client.get("/api/health", headers={"x-request-id": "req-123"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req-123"


def test_healthcheck_generates_request_id_when_missing(client) -> None:
    response = client.get("/api/health")
    request_id = response.headers["x-request-id"]

    assert response.status_code == 200
    assert request_id
    assert request_id == get_or_create_request_id(request_id)


def test_metrics_endpoint_exposes_http_metrics(client) -> None:
    client.get("/api/health", headers={"x-request-id": "metrics-health"})

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "filesh_http_requests_total" in response.text
    assert 'path="/api/health"' in response.text


def test_cleanup_events_include_request_correlation_id(client, event_publisher) -> None:
    headers = register_and_login(client, "obs@example.com", "obs-user")
    root_response = client.get("/api/folders/root", headers=headers)

    response = client.post(
        "/api/files/upload/init",
        headers={**headers, "x-request-id": "cleanup-correlation-id"},
        json={
            "folder_id": root_response.json()["id"],
            "filename": "temp.txt",
            "expected_size": 4,
        },
    )

    assert response.status_code == 201

    fail_response = client.post(
        "/api/files/upload/fail",
        headers={**headers, "x-request-id": "cleanup-correlation-id"},
        json={
            "upload_session_id": response.json()["session_id"],
            "failure_reason": "cancelled",
        },
    )

    assert fail_response.status_code == 204
    assert (
        event_publisher.events[-1].payload["metadata"]["correlation_id"] == "cleanup-correlation-id"
    )


def test_cleanup_events_include_trace_context(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.tracing_enabled", True)
    span_context = SpanContext(
        trace_id=0x1234567890ABCDEF1234567890ABCDEF,
        span_id=0x1234567890ABCDEF,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
        trace_state=trace.DEFAULT_TRACE_STATE,
    )
    context = trace.set_span_in_context(NonRecordingSpan(span_context))
    token = attach(context)
    try:
        event = build_cleanup_event("file.delete_requested")
    finally:
        detach(token)

    assert TRACE_CONTEXT_METADATA_KEY in event["metadata"]
    assert "traceparent" in event["metadata"][TRACE_CONTEXT_METADATA_KEY]


def test_request_log_extra_includes_trace_ids_from_current_span() -> None:
    span_context = SpanContext(
        trace_id=0x1234567890ABCDEF1234567890ABCDEF,
        span_id=0x1234567890ABCDEF,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
        trace_state=trace.DEFAULT_TRACE_STATE,
    )
    context = trace.set_span_in_context(NonRecordingSpan(span_context))
    token = attach(context)
    try:
        payload = request_log_extra(action="test")
    finally:
        detach(token)

    assert payload["trace_id"] == "1234567890abcdef1234567890abcdef"
    assert payload["span_id"] == "1234567890abcdef"


def test_request_context_filter_defaults_trace_ids_when_missing() -> None:
    record = logging.LogRecord(
        name="tests.observability",
        level=20,
        pathname=__file__,
        lineno=0,
        msg="hello",
        args=(),
        exc_info=None,
    )

    RequestContextFilter().filter(record)

    assert record.trace_id == "-"
    assert record.span_id == "-"
