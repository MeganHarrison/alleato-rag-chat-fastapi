"""
FastAPI middleware for comprehensive request tracing and monitoring.
"""

import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .tracing import get_tracer


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware for tracing HTTP requests and responses."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.tracer = get_tracer()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Start timing
        start_time = time.time()
        
        # Extract request info
        method = request.method
        url = str(request.url)
        endpoint = request.url.path
        user_agent = request.headers.get("user-agent", "")
        client_ip = request.client.host if request.client else "unknown"
        
        # Start tracing span
        with self.tracer.trace_operation(
            "http_request",
            request_id=request_id,
            method=method,
            endpoint=endpoint,
            user_agent=user_agent,
            client_ip=client_ip
        ) as span:
            
            try:
                # Process request
                response = await call_next(request)
                
                # Calculate duration
                duration = time.time() - start_time
                
                # Add response info to span
                span.set_attribute("status_code", response.status_code)
                span.set_attribute("response_size", getattr(response, "content_length", 0))
                
                # Log request details
                self.tracer.log_request(method, endpoint, response.status_code, duration)
                
                # Add custom headers
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Response-Time"] = f"{duration:.3f}s"
                
                return response
                
            except Exception as e:
                duration = time.time() - start_time
                
                # Log error
                self.tracer.logger.error(
                    "Request processing failed",
                    request_id=request_id,
                    method=method,
                    endpoint=endpoint,
                    error=str(e),
                    duration=duration
                )
                
                # Re-raise exception
                raise


class ChatTracingMiddleware(BaseHTTPMiddleware):
    """Specialized middleware for chat endpoint tracing."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.tracer = get_tracer()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Only process chat endpoints
        if not request.url.path.startswith("/chat"):
            return await call_next(request)
        
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        
        # Extract chat-specific information
        chat_type = "streaming" if "stream" in request.url.path else "standard"
        
        with self.tracer.trace_operation(
            "chat_request",
            request_id=request_id,
            chat_type=chat_type
        ) as span:
            
            try:
                # Try to extract message from request body
                if request.method == "POST":
                    body = await request.body()
                    if body:
                        try:
                            import json
                            data = json.loads(body.decode())
                            message = data.get("message", "")
                            
                            # Add chat context to span
                            span.set_attribute("message_length", len(message))
                            span.set_attribute("has_conversation_history", 
                                             bool(data.get("conversation_history")))
                            span.set_attribute("session_id", 
                                             data.get("session_id", ""))
                            
                            # Log chat context
                            self.tracer.logger.info(
                                "Chat request received",
                                request_id=request_id,
                                chat_type=chat_type,
                                message_length=len(message),
                                has_history=bool(data.get("conversation_history"))
                            )
                        except json.JSONDecodeError:
                            pass
                
                # Recreate request with body
                request = Request(scope=request.scope, receive=request._receive)
                response = await call_next(request)
                
                return response
                
            except Exception as e:
                self.tracer.logger.error(
                    "Chat request failed",
                    request_id=request_id,
                    chat_type=chat_type,
                    error=str(e)
                )
                raise