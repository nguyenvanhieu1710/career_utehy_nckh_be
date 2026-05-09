from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.core.database import SessionLocal
from app.services.system_log_service import SystemLogService
from app.utils.auth import verify_token
import logging
import time

logger = logging.getLogger(__name__)

class AnalyticsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Skip logging for certain paths to avoid noise
        skip_paths = [
            "/uploads", 
            "/static", 
            "/docs", 
            "/redoc", 
            "/openapi.json", 
            "/health", 
            "/", 
            "/favicon.ico"
        ]
        
        path = request.url.path
        
        # 1. Skip logging for certain paths to avoid noise
        skip_prefixes = [
            "/uploads", 
            "/static", 
            "/docs", 
            "/redoc", 
            "/openapi.json", 
            "/health", 
            "/favicon.ico",
            "/api/v1/auth/login",
            "/api/v1/auth/signup"
        ]
        
        # Check if path is exactly "/" or starts with any skip prefix
        if path == "/" or any(path.startswith(p) for p in skip_prefixes):
            return await call_next(request)

        # 2. Start timer
        start_time = time.perf_counter()

        # 3. Process the request
        response = await call_next(request)

        # 4. Calculate duration
        process_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

        # 5. Log the visit asynchronously
        try:
            async with SessionLocal() as db:
                # Try to identify user if token exists
                user_id = None
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    try:
                        token = auth_header.split(" ")[1]
                        payload = verify_token(token)
                        if payload:
                            user_id = payload.get("user_id")
                    except Exception:
                        pass # Ignore invalid tokens in middleware

                # Get client IP address accurately
                ip_address = request.headers.get("x-forwarded-for")
                if ip_address:
                    ip_address = ip_address.split(",")[0]
                else:
                    ip_address = request.client.host if request.client else "unknown"

                # Log as a 'visit' action with duration
                await SystemLogService.log_visit(
                    db=db,
                    path=path,
                    method=request.method,
                    ip_address=ip_address,
                    user_agent=request.headers.get("user-agent"),
                    user_id=user_id,
                    duration_ms=round(process_time, 2)
                )
        except Exception as e:
            # We don't want analytics to break the main application flow
            logger.error(f"Analytics logging failed: {str(e)}")

        return response
