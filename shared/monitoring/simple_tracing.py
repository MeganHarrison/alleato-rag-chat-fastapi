"""
Simple tracing and monitoring for the RAG system without external dependencies.
This provides basic logging and monitoring functionality.
"""

import time
import logging
import json
from typing import Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager


class SimpleTracer:
    """Simple tracer for basic monitoring without external dependencies."""
    
    def __init__(self, service_name: str = "alleato-rag-agent"):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.INFO)
        
        # Setup console handler if none exists
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        print(f"✅ Simple tracing enabled for {service_name}")
    
    @contextmanager
    def trace_operation(self, operation_name: str, **attributes):
        """Simple context manager for tracing operations."""
        start_time = time.time()
        
        # Log operation start
        self.logger.info(
            f"Starting {operation_name}",
            extra={"operation": operation_name, "attributes": attributes}
        )
        
        try:
            yield self
            duration = time.time() - start_time
            self.logger.info(
                f"Completed {operation_name} in {duration:.3f}s",
                extra={
                    "operation": operation_name,
                    "duration": duration,
                    "success": True
                }
            )
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(
                f"Failed {operation_name} after {duration:.3f}s: {str(e)}",
                extra={
                    "operation": operation_name,
                    "duration": duration,
                    "success": False,
                    "error": str(e)
                }
            )
            raise
    
    def trace_search_operation(self, search_type: str):
        """Simple decorator for tracing search operations."""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.trace_operation(f"search_{search_type}", search_type=search_type):
                    result = await func(*args, **kwargs)
                    
                    # Log result metrics
                    result_count = len(result) if isinstance(result, list) else 1
                    self.logger.info(
                        f"Search {search_type} returned {result_count} results"
                    )
                    
                    return result
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.trace_operation(f"search_{search_type}", search_type=search_type):
                    return func(*args, **kwargs)
            
            return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
        return decorator
    
    def trace_agent_execution(self, agent_type: str):
        """Simple decorator for tracing AI agent execution."""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.trace_operation(f"agent_{agent_type}", agent_type=agent_type):
                    return await func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.trace_operation(f"agent_{agent_type}", agent_type=agent_type):
                    return func(*args, **kwargs)
            
            return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
        return decorator
    
    def log_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Log HTTP request details."""
        self.logger.info(
            f"{method} {endpoint} - {status_code} - {duration:.3f}s",
            extra={
                "method": method,
                "endpoint": endpoint,
                "status_code": status_code,
                "duration": duration,
                "type": "http_request"
            }
        )
    
    def instrument_fastapi(self, app):
        """Simple FastAPI instrumentation (no-op but compatible)."""
        print("✅ Simple FastAPI monitoring enabled")
    
    def start_metrics_server(self, port: int = 9090):
        """Simple metrics server (no-op but compatible)."""
        print(f"⚠️  Simple monitoring active - advanced metrics disabled")


# Global simple tracer
_simple_tracer = None

def get_simple_tracer() -> SimpleTracer:
    """Get the global simple tracer instance."""
    global _simple_tracer
    if _simple_tracer is None:
        _simple_tracer = SimpleTracer()
    return _simple_tracer