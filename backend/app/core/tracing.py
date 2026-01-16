"""OpenTelemetry tracing configuration and utilities.

This module sets up distributed tracing for the application using OpenTelemetry.
It provides decorators for tracing key operations and initialization for
exporting traces to a backend (e.g., Jaeger, OTLP).
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Global tracer provider
_tracer_provider = None
_tracer = None


def init_tracing(service_name: str = "code-doc-assistant") -> Any:
    """Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service for tracing

    Returns:
        Configured tracer or None if tracing is disabled
    """
    global _tracer_provider, _tracer

    # Check if tracing is enabled
    if not settings.enable_tracing:
        logger.info("tracing_disabled", message="OpenTelemetry tracing is disabled")
        return None

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        # Create resource with service metadata
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": getattr(settings, "version", "0.1.0"),
                "deployment.environment": settings.environment,
            }
        )

        # Create tracer provider
        _tracer_provider = TracerProvider(resource=resource)

        # Add span processor
        # For MVP, use console exporter. In production, use OTLP or Jaeger
        if settings.tracing_endpoint:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            otlp_exporter = OTLPSpanExporter(endpoint=settings.tracing_endpoint, insecure=True)
            span_processor = BatchSpanProcessor(otlp_exporter)
        else:
            # Fallback to console exporter for development
            console_exporter = ConsoleSpanExporter()
            span_processor = BatchSpanProcessor(console_exporter)

        _tracer_provider.add_span_processor(span_processor)

        # Set global tracer provider
        trace.set_tracer_provider(_tracer_provider)

        # Get tracer
        _tracer = trace.get_tracer(__name__)

        logger.info(
            "tracing_initialized",
            service_name=service_name,
            endpoint=settings.tracing_endpoint or "console",
        )

        return _tracer

    except ImportError:
        logger.warning("tracing_import_failed", message="opentelemetry packages not installed")
        return None
    except Exception as e:
        logger.error("tracing_init_failed", error=str(e))
        return None


def get_tracer():
    """Get the configured tracer instance.

    Returns:
        Tracer instance or None if not initialized
    """
    global _tracer

    if _tracer is None:
        _tracer = init_tracing()

    return _tracer


def trace_operation(operation_name: str | None = None):
    """Decorator to trace a function operation.

    Args:
        operation_name: Name for the span (defaults to function name)

    Example:
        @trace_operation("parse_code")
        async def parse_code(file_path: str):
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            if tracer is None:
                return await func(*args, **kwargs)

            name = operation_name or func.__name__
            with tracer.start_as_current_span(name) as span:
                # Add function name as attribute
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                # Add common attributes from kwargs if they exist
                if "codebase_id" in kwargs:
                    span.set_attribute("codebase_id", str(kwargs["codebase_id"]))
                if "session_id" in kwargs:
                    span.set_attribute("session_id", str(kwargs["session_id"]))
                if "query" in kwargs:
                    span.set_attribute("query.length", len(kwargs["query"]))

                try:
                    result = await func(*args, **kwargs)
                    span.set_status("OK")
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status("ERROR", str(e))
                    raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer()
            if tracer is None:
                return func(*args, **kwargs)

            name = operation_name or func.__name__
            with tracer.start_as_current_span(name) as span:
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)

                if "codebase_id" in kwargs:
                    span.set_attribute("codebase_id", str(kwargs["codebase_id"]))
                if "session_id" in kwargs:
                    span.set_attribute("session_id", str(kwargs["session_id"]))

                try:
                    result = func(*args, **kwargs)
                    span.set_status("OK")
                    return result
                except Exception as e:
                    span.record_exception(e)
                    span.set_status("ERROR", str(e))
                    raise

        # Return appropriate wrapper based on function type
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def trace_parse(func: Callable) -> Callable:
    """Decorator for tracing code parsing operations.

    Adds specific attributes for parsing operations like file count,
    file types, and parsing duration.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        tracer = get_tracer()
        if tracer is None:
            return await func(*args, **kwargs)

        with tracer.start_as_current_span("code.parse") as span:
            span.set_attribute("operation", "parse_code")
            span.set_attribute("function.name", func.__name__)

            try:
                result = await func(*args, **kwargs)

                # Add result attributes if available
                if hasattr(result, "__len__"):
                    span.set_attribute("result.count", len(result))

                span.set_status("OK")
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status("ERROR", str(e))
                raise

    return wrapper


def trace_embed(func: Callable) -> Callable:
    """Decorator for tracing embedding generation operations.

    Adds specific attributes for embedding operations like chunk count,
    embedding dimensions, and model used.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        tracer = get_tracer()
        if tracer is None:
            return await func(*args, **kwargs)

        with tracer.start_as_current_span("embedding.generate") as span:
            span.set_attribute("operation", "generate_embeddings")
            span.set_attribute("function.name", func.__name__)

            # Track input size
            if "texts" in kwargs:
                span.set_attribute("input.count", len(kwargs["texts"]))
            elif args and isinstance(args[0], list):
                span.set_attribute("input.count", len(args[0]))

            try:
                result = await func(*args, **kwargs)

                # Add result attributes
                if isinstance(result, list) and result:
                    span.set_attribute("output.count", len(result))
                    if isinstance(result[0], list):
                        span.set_attribute("embedding.dimension", len(result[0]))

                span.set_status("OK")
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status("ERROR", str(e))
                raise

    return wrapper


def trace_retrieve(func: Callable) -> Callable:
    """Decorator for tracing vector retrieval operations.

    Adds specific attributes for retrieval operations like query text,
    top-k value, and retrieval scores.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        tracer = get_tracer()
        if tracer is None:
            return await func(*args, **kwargs)

        with tracer.start_as_current_span("vector.retrieve") as span:
            span.set_attribute("operation", "retrieve_chunks")
            span.set_attribute("function.name", func.__name__)

            # Track query info
            if "query" in kwargs:
                span.set_attribute("query.length", len(kwargs["query"]))
            elif args and isinstance(args[0], str):
                span.set_attribute("query.length", len(args[0]))

            if "top_k" in kwargs:
                span.set_attribute("retrieval.top_k", kwargs["top_k"])

            try:
                result = await func(*args, **kwargs)

                # Add result attributes
                if isinstance(result, list):
                    span.set_attribute("result.count", len(result))
                    if result and hasattr(result[0], "score"):
                        scores = [r.score for r in result if hasattr(r, "score")]
                        if scores:
                            span.set_attribute("retrieval.min_score", min(scores))
                            span.set_attribute("retrieval.max_score", max(scores))
                            span.set_attribute("retrieval.avg_score", sum(scores) / len(scores))

                span.set_status("OK")
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status("ERROR", str(e))
                raise

    return wrapper


def trace_generate(func: Callable) -> Callable:
    """Decorator for tracing LLM response generation operations.

    Adds specific attributes for generation operations like prompt length,
    response length, token usage, and model used.
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        tracer = get_tracer()
        if tracer is None:
            return await func(*args, **kwargs)

        with tracer.start_as_current_span("llm.generate") as span:
            span.set_attribute("operation", "generate_response")
            span.set_attribute("function.name", func.__name__)

            # Track query info
            if "query" in kwargs:
                span.set_attribute("query.length", len(kwargs["query"]))
            elif args and isinstance(args[0], str):
                span.set_attribute("query.length", len(args[0]))

            try:
                result = await func(*args, **kwargs)

                # Extract metrics from result
                # Result format: (response_text, citations, token_count)
                if isinstance(result, tuple) and len(result) >= 3:
                    response_text, citations, token_count = result[:3]
                    span.set_attribute("response.length", len(response_text))
                    span.set_attribute("response.token_count", token_count)
                    if citations:
                        span.set_attribute("response.citation_count", len(citations))

                span.set_status("OK")
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status("ERROR", str(e))
                raise

    return wrapper


def shutdown_tracing() -> None:
    """Shutdown the tracer provider and flush any pending spans.

    Should be called when the application is shutting down.
    """
    global _tracer_provider

    if _tracer_provider is not None:
        _tracer_provider.shutdown()
        _tracer_provider = None
        _tracer = None
        logger.info("tracing_shutdown", message="OpenTelemetry tracing shutdown complete")


# Initialize tracing on module import
_tracer = init_tracing()
