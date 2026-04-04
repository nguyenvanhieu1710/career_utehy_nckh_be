"""
FastAPI Rate Limiting Middleware
Integrates rate limiting into FastAPI request/response cycle
"""
import time
import logging
from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from .rate_limiter import rate_limiter, RateLimitCheckResult
from .rate_limit_config import rate_limit_config
from app.utils.auth import verify_token, get_current_user_permissions

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting"""
    
    def __init__(self, app, enabled: bool = True, skip_paths: list = None):
        super().__init__(app)
        self.enabled = enabled and rate_limit_config.is_enabled()
        self.skip_paths = skip_paths or [
            "/docs",
            "/redoc", 
            "/openapi.json",
            "/health",
            "/",
            "/favicon.ico"
        ]
        
        # Performance tracking
        self._request_count = 0
        self._total_processing_time = 0.0
    
    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        """Process request with rate limiting"""
        start_time = time.time()
        
        # Skip rate limiting if disabled or for certain paths
        if not self.enabled or self._should_skip_path(request.url.path):
            response = await call_next(request)
            return response
        
        try:
            # Extract request information
            request_info = await self._extract_request_info(request)
            
            # Check rate limits
            rate_limit_result = await rate_limiter.check_rate_limit(request_info)
            
            # If rate limit exceeded, return 429
            if not rate_limit_result.allowed:
                return await self._create_rate_limit_response(rate_limit_result)
            
            # Process request normally
            response = await call_next(request)
            
            # Add rate limit headers to response
            self._add_rate_limit_headers(response, rate_limit_result)
            
            # Update performance metrics
            processing_time = time.time() - start_time
            self._update_metrics(processing_time)
            
            return response
            
        except Exception as e:
            logger.error(f"Rate limiting middleware error: {e}")
            
            # On error, allow request to proceed (fail-open)
            response = await call_next(request)
            
            # Add error header for debugging
            response.headers["X-RateLimit-Error"] = "middleware-error"
            
            return response
    
    def _should_skip_path(self, path: str) -> bool:
        """Check if path should skip rate limiting"""
        for skip_path in self.skip_paths:
            if path.startswith(skip_path):
                return True
        return False
    
    async def _extract_request_info(self, request: Request) -> Dict[str, Any]:
        """Extract information needed for rate limiting"""
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Get endpoint path
        endpoint = request.url.path
        
        # Try to get user information from token
        user_id = None
        permissions = []
        is_premium = False
        
        try:
            # Check for Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                
                # Verify token and get user info
                payload = verify_token(token)
                if payload:
                    user_id = payload.get("user_id")
                    
                    # Get user permissions (this might require DB call)
                    # For now, we'll use basic info from token
                    permissions = payload.get("permissions", [])
                    is_premium = payload.get("is_premium", False)
                    
        except Exception as e:
            logger.debug(f"Token verification failed in rate limiting: {e}")
            # Continue with anonymous user
            pass
        
        return {
            "endpoint": endpoint,
            "user_id": user_id,
            "ip_address": client_ip,
            "permissions": permissions,
            "is_premium": is_premium,
            "method": request.method,
            "user_agent": request.headers.get("User-Agent", ""),
            "timestamp": time.time()
        }
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proxy support"""
        # Check for forwarded headers (common in production)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"
    
    async def _create_rate_limit_response(self, result: RateLimitCheckResult) -> JSONResponse:
        """Create HTTP 429 response for rate limit exceeded"""
        
        # Get the most restrictive result for error details
        restrictive_result = result.most_restrictive_result
        
        error_detail = {
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Limit: {restrictive_result.limit} requests per {restrictive_result.window_size} seconds",
            "limit": restrictive_result.limit,
            "window": restrictive_result.window_size,
            "current_count": restrictive_result.current_count,
            "reset_time": restrictive_result.reset_time,
            "retry_after": result.retry_after,
            "endpoint": result.endpoint,
            "user_type": result.user_type.value
        }
        
        # Create response
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=error_detail
        )
        
        # Add rate limit headers
        for header_name, header_value in result.headers.items():
            response.headers[header_name] = header_value
        
        # Add standard rate limit headers
        response.headers["X-RateLimit-Scope"] = "endpoint"
        response.headers["X-RateLimit-Identifier"] = result.identifier
        
        logger.info(f"Rate limit exceeded: {result.endpoint} for {result.identifier}")
        
        return response
    
    def _add_rate_limit_headers(self, response: Response, result: RateLimitCheckResult):
        """Add rate limit headers to successful response"""
        if not rate_limit_config.include_headers:
            return
        
        # Add all headers from rate limit result
        for header_name, header_value in result.headers.items():
            response.headers[header_name] = header_value
        
        # Add additional informational headers
        response.headers["X-RateLimit-Scope"] = "endpoint"
        response.headers["X-RateLimit-Identifier"] = result.identifier
        response.headers["X-RateLimit-UserType"] = result.user_type.value
    
    def _update_metrics(self, processing_time: float):
        """Update middleware performance metrics"""
        self._request_count += 1
        self._total_processing_time += processing_time
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get middleware performance metrics"""
        avg_processing_time = (
            self._total_processing_time / self._request_count 
            if self._request_count > 0 else 0
        )
        
        return {
            "enabled": self.enabled,
            "request_count": self._request_count,
            "total_processing_time": self._total_processing_time,
            "average_processing_time": avg_processing_time,
            "skip_paths": self.skip_paths
        }


class RateLimitExceptionHandler:
    """Custom exception handler for rate limiting errors"""
    
    @staticmethod
    async def rate_limit_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Handle rate limit exceptions"""
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": str(exc.detail),
                    "timestamp": time.time(),
                    "path": request.url.path
                }
            )
        
        # Re-raise other exceptions
        raise exc


# Utility functions for manual rate limiting
async def check_rate_limit_manual(
    request: Request,
    endpoint: str = None,
    user_id: str = None,
    custom_limit: int = None,
    custom_window: int = None
) -> RateLimitCheckResult:
    """
    Manual rate limit check for specific use cases
    
    Args:
        request: FastAPI request object
        endpoint: Override endpoint path
        user_id: Override user ID
        custom_limit: Custom rate limit
        custom_window: Custom time window
    
    Returns:
        RateLimitCheckResult
    """
    # Extract basic request info
    client_ip = request.client.host if request.client else "unknown"
    actual_endpoint = endpoint or request.url.path
    
    request_info = {
        "endpoint": actual_endpoint,
        "user_id": user_id,
        "ip_address": client_ip,
        "permissions": [],
        "is_premium": False,
        "method": request.method,
        "timestamp": time.time()
    }
    
    # If custom limits provided, temporarily modify config
    if custom_limit and custom_window:
        # This would require extending the rate limiter to support custom rules
        # For now, use standard checking
        pass
    
    return await rate_limiter.check_rate_limit(request_info)


def require_rate_limit(
    limit: int = None,
    window: int = None,
    user_types: list = None
):
    """
    Decorator for endpoint-specific rate limiting
    
    Usage:
        @app.get("/api/special")
        @require_rate_limit(limit=5, window=60)
        async def special_endpoint():
            return {"message": "success"}
    """
    def decorator(func):
        # Store rate limit info in function metadata
        func._rate_limit_config = {
            "limit": limit,
            "window": window,
            "user_types": user_types
        }
        return func
    return decorator


# Global middleware instance
rate_limit_middleware = None


def create_rate_limit_middleware(
    enabled: bool = True,
    skip_paths: list = None
) -> RateLimitMiddleware:
    """Create and configure rate limit middleware"""
    global rate_limit_middleware
    rate_limit_middleware = RateLimitMiddleware(
        app=None,  # Will be set when added to FastAPI
        enabled=enabled,
        skip_paths=skip_paths
    )
    return rate_limit_middleware


def get_rate_limit_middleware() -> Optional[RateLimitMiddleware]:
    """Get the global rate limit middleware instance"""
    return rate_limit_middleware