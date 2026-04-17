import logging

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.v1.share_access import router as share_access_router
from app.core.config import settings
from app.core.observability import (
    configure_logging,
    current_time,
    get_or_create_request_id,
    observe_http_request,
    render_metrics,
    request_log_extra,
    reset_request_id,
    set_request_id,
)
from app.core.tracing import (
    HTTP_SPAN_KIND,
    configure_tracing,
    get_tracer,
    record_span_exception,
    set_span_attributes,
)

configure_logging()
configure_tracing(service_name=settings.otel_service_name)
logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)

app = FastAPI(
    title="File Sharing Web Application API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(share_access_router)


@app.middleware("http")
async def observe_requests(request: Request, call_next) -> Response:
    request_id = get_or_create_request_id(request.headers.get("x-request-id"))
    token = set_request_id(request_id)
    started_at = current_time()
    path_template = request.url.path
    try:
        with tracer.start_as_current_span(
            f"{request.method} {path_template}",
            kind=HTTP_SPAN_KIND,
        ) as span:
            set_span_attributes(
                span,
                {
                    "http.method": request.method,
                    "http.target": str(request.url.path),
                    "http.scheme": request.url.scheme,
                    "http.client_ip": request.client.host if request.client else None,
                    "request.id": request_id,
                },
            )
            try:
                response = await call_next(request)
            except Exception as exc:
                duration = current_time() - started_at
                observe_http_request(request.method, path_template, 500, duration)
                record_span_exception(span, exc)
                logger.exception(
                    "http request failed",
                    extra=request_log_extra(
                        method=request.method,
                        path=path_template,
                        status_code=500,
                        duration_ms=round(duration * 1000, 2),
                    ),
                )
                raise
            if request.scope.get("route") is not None:
                path_template = getattr(request.scope["route"], "path", path_template)
            span.update_name(f"{request.method} {path_template}")
            set_span_attributes(
                span,
                {
                    "http.route": path_template,
                    "http.status_code": response.status_code,
                },
            )
            duration = current_time() - started_at
            observe_http_request(request.method, path_template, response.status_code, duration)
            response.headers["x-request-id"] = request_id
            logger.info(
                "http request completed",
                extra=request_log_extra(
                    method=request.method,
                    path=path_template,
                    status_code=response.status_code,
                    duration_ms=round(duration * 1000, 2),
                ),
            )
            return response
    finally:
        reset_request_id(token)


@app.get("/metrics", tags=["system"])
async def metrics() -> Response:
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)


@app.get("/", tags=["system"])
async def root() -> dict[str, str]:
    return {
        "service": "backend",
        "environment": settings.app_env,
        "status": "ok",
    }
