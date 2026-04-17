from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagate import set_global_textmap
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from app.core.config import settings

TRACE_CONTEXT_METADATA_KEY = "trace_context"


def configure_tracing(*, service_name: str | None = None) -> None:
    if not settings.tracing_enabled:
        return
    if getattr(configure_tracing, "_configured", False):
        return

    resource = Resource.create(
        {
            "service.name": service_name or settings.otel_service_name,
            "service.namespace": settings.otel_service_namespace,
            "deployment.environment": settings.app_env,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        insecure=settings.otel_exporter_otlp_insecure,
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    set_global_textmap(TraceContextTextMapPropagator())
    configure_tracing._configured = True


def get_tracer(name: str):
    return trace.get_tracer(name)


def inject_trace_context(metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(metadata or {})
    if not settings.tracing_enabled:
        return payload

    carrier: dict[str, str] = {}
    TraceContextTextMapPropagator().inject(carrier)
    if carrier:
        payload[TRACE_CONTEXT_METADATA_KEY] = carrier
    return payload


def extract_trace_context(metadata: Mapping[str, Any] | None = None):
    if not settings.tracing_enabled:
        return otel_context.get_current()
    carrier = metadata.get(TRACE_CONTEXT_METADATA_KEY, {}) if metadata else {}
    if not isinstance(carrier, dict):
        return otel_context.get_current()
    normalized_carrier = {str(key): str(value) for key, value in carrier.items()}
    return TraceContextTextMapPropagator().extract(normalized_carrier)


def record_span_exception(span, exc: Exception) -> None:
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))


def set_span_attributes(span, attributes: Mapping[str, Any]) -> None:
    for key, value in attributes.items():
        if value is None:
            continue
        span.set_attribute(key, value)


HTTP_SPAN_KIND = SpanKind.SERVER
WORKER_SPAN_KIND = SpanKind.CONSUMER
