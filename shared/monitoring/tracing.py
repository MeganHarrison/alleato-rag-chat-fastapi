"""
Comprehensive tracing and monitoring setup for Alleato RAG Agent.

This module provides:
- OpenTelemetry distributed tracing
- Structured logging with rich formatting
- Performance metrics collection
- Request/response monitoring
- AI agent execution tracing
"""

import os
import time
import structlog
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager
import asyncio

# Optional OpenTelemetry imports - graceful degradation if not available
try:
    from opentelemetry import trace, metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
    TRACING_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  OpenTelemetry not available: {e}")
    TRACING_AVAILABLE = False

# Optional Prometheus imports
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    METRICS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Prometheus client not available: {e}")
    METRICS_AVAILABLE = False


class NoOpTracer:
    """No-operation tracer for when OpenTelemetry is not available."""
    
    def start_as_current_span(self, name, **kwargs):
        return NoOpSpan()
    
    def get_tracer(self, name):
        return self


class NoOpSpan:
    """No-operation span for when OpenTelemetry is not available."""
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def set_attribute(self, key, value):
        pass


class NoOpMetric:
    """No-operation metric for when Prometheus is not available."""
    
    def labels(self, **kwargs):
        return self
    
    def inc(self, value=1):
        pass
    
    def observe(self, value):
        pass
    
    def set(self, value):
        pass


class AlleartoTracer:
    """Main tracing and monitoring class for the RAG system."""
    
    def __init__(self, service_name: str = "alleato-rag-agent"):
        self.service_name = service_name
        self.tracer = None
        self.meter = None
        self.logger = None
        
        # Metrics
        self.request_count = None
        self.request_duration = None
        self.agent_execution_duration = None
        self.search_operations = None
        self.active_connections = None
        
        self._setup_tracing()
        self._setup_metrics()
        self._setup_logging()
    
    def _setup_tracing(self):
        """Setup OpenTelemetry distributed tracing."""
        if not TRACING_AVAILABLE:
            print("⚠️  Tracing disabled - OpenTelemetry not available")
            self.tracer = NoOpTracer()
            return
        
        # Configure tracer provider
        trace.set_tracer_provider(TracerProvider())
        
        # Setup Jaeger exporter (optional - only if Jaeger is available)
        jaeger_endpoint = os.getenv("JAEGER_ENDPOINT", "http://localhost:14268/api/traces")
        
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name="localhost",
                agent_port=6831,
                collector_endpoint=jaeger_endpoint,
            )
            span_processor = BatchSpanProcessor(jaeger_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            print(f"✅ Jaeger tracing enabled: {jaeger_endpoint}")
        except Exception as e:
            print(f"⚠️  Jaeger not available, using console tracing: {e}")
        
        self.tracer = trace.get_tracer(self.service_name)
    
    def _setup_metrics(self):
        """Setup Prometheus metrics."""
        if not METRICS_AVAILABLE:
            print("⚠️  Metrics disabled - Prometheus client not available")
            self.request_count = NoOpMetric()
            self.request_duration = NoOpMetric()
            self.agent_execution_duration = NoOpMetric()
            self.search_operations = NoOpMetric()
            self.active_connections = NoOpMetric()
            self.vector_similarity_scores = NoOpMetric()
            return
        
        # Request metrics
        self.request_count = Counter(
            'alleato_requests_total',
            'Total number of requests',
            ['method', 'endpoint', 'status']
        )
        
        self.request_duration = Histogram(
            'alleato_request_duration_seconds',
            'Request duration in seconds',
            ['method', 'endpoint']
        )
        
        # AI Agent metrics
        self.agent_execution_duration = Histogram(
            'alleato_agent_execution_seconds',
            'AI agent execution time',
            ['agent_type', 'success']
        )
        
        self.search_operations = Counter(
            'alleato_search_operations_total',
            'Search operations performed',
            ['search_type', 'success']
        )
        
        # Database metrics
        self.active_connections = Gauge(
            'alleato_db_connections_active',
            'Active database connections'
        )
        
        # Vector search metrics
        self.vector_similarity_scores = Histogram(
            'alleato_vector_similarity_scores',
            'Vector similarity scores distribution',
            buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        )
        
        print(f"✅ Prometheus metrics enabled on :9090/metrics")
    
    def _setup_logging(self):
        """Setup structured logging with rich formatting."""
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        
        self.logger = structlog.get_logger(self.service_name)
        print(f"✅ Structured logging enabled")
    
    def instrument_fastapi(self, app):
        """Instrument FastAPI app with tracing."""
        if not TRACING_AVAILABLE:
            print("⚠️  FastAPI instrumentation disabled - OpenTelemetry not available")
            return
            
        try:
            FastAPIInstrumentor.instrument_app(app, tracer_provider=trace.get_tracer_provider())
            HTTPXClientInstrumentor().instrument()
            AsyncPGInstrumentor().instrument()
            print(f"✅ FastAPI instrumentation enabled")
        except Exception as e:
            print(f"⚠️  FastAPI instrumentation failed: {e}")
    
    @contextmanager
    def trace_operation(self, operation_name: str, **attributes):
        """Context manager for tracing operations."""
        with self.tracer.start_as_current_span(operation_name) as span:
            # Add attributes to span
            for key, value in attributes.items():
                span.set_attribute(key, str(value))
            
            start_time = time.time()
            try:
                yield span
                span.set_attribute("success", True)
            except Exception as e:
                span.set_attribute("success", False)
                span.set_attribute("error.message", str(e))
                span.set_attribute("error.type", type(e).__name__)
                raise
            finally:
                duration = time.time() - start_time
                span.set_attribute("duration_seconds", duration)
    
    def trace_agent_execution(self, agent_type: str):
        """Decorator for tracing AI agent execution."""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.trace_operation(
                    f"agent_execution_{agent_type}",
                    agent_type=agent_type
                ) as span:
                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        self.agent_execution_duration.labels(
                            agent_type=agent_type,
                            success="true"
                        ).observe(time.time() - start_time)
                        
                        # Log successful execution
                        self.logger.info(
                            "Agent execution completed",
                            agent_type=agent_type,
                            duration=time.time() - start_time,
                            success=True
                        )
                        return result
                    except Exception as e:
                        self.agent_execution_duration.labels(
                            agent_type=agent_type,
                            success="false"
                        ).observe(time.time() - start_time)
                        
                        # Log failed execution
                        self.logger.error(
                            "Agent execution failed",
                            agent_type=agent_type,
                            duration=time.time() - start_time,
                            error=str(e),
                            success=False
                        )
                        raise
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.trace_operation(
                    f"agent_execution_{agent_type}",
                    agent_type=agent_type
                ):
                    return func(*args, **kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
    
    def trace_search_operation(self, search_type: str):
        """Decorator for tracing search operations."""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.trace_operation(
                    f"search_{search_type}",
                    search_type=search_type
                ) as span:
                    try:
                        result = await func(*args, **kwargs)
                        
                        # Record search metrics
                        self.search_operations.labels(
                            search_type=search_type,
                            success="true"
                        ).inc()
                        
                        # Log search results
                        result_count = len(result) if isinstance(result, list) else 1
                        span.set_attribute("result_count", result_count)
                        
                        # Record similarity scores if available
                        if isinstance(result, list) and result:
                            if hasattr(result[0], 'similarity'):
                                for item in result:
                                    self.vector_similarity_scores.observe(item.similarity)
                        
                        self.logger.info(
                            "Search operation completed",
                            search_type=search_type,
                            result_count=result_count,
                            success=True
                        )
                        
                        return result
                    except Exception as e:
                        self.search_operations.labels(
                            search_type=search_type,
                            success="false"
                        ).inc()
                        
                        self.logger.error(
                            "Search operation failed",
                            search_type=search_type,
                            error=str(e),
                            success=False
                        )
                        raise
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else func
        return decorator
    
    def log_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Log HTTP request details."""
        self.request_count.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()
        
        self.request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        self.logger.info(
            "HTTP request processed",
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            duration=duration
        )
    
    def update_db_connections(self, count: int):
        """Update active database connections gauge."""
        self.active_connections.set(count)
    
    def start_metrics_server(self, port: int = 9090):
        """Start Prometheus metrics server."""
        try:
            start_http_server(port)
            print(f"✅ Metrics server started on port {port}")
        except Exception as e:
            print(f"⚠️  Could not start metrics server: {e}")


# Global tracer instance
tracer = None

def get_tracer() -> AlleartoTracer:
    """Get the global tracer instance."""
    global tracer
    if tracer is None:
        tracer = AlleartoTracer()
    return tracer

def initialize_tracing(app, service_name: str = "alleato-rag-agent"):
    """Initialize tracing for the FastAPI application."""
    global tracer
    tracer = AlleartoTracer(service_name)
    tracer.instrument_fastapi(app)
    tracer.start_metrics_server()
    return tracer