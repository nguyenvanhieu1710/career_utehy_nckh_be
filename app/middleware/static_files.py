from fastapi import Request, Response
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
import os
import time
from typing import Callable


class StaticFileSecurityMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers and caching for static files
    """
    
    def __init__(self, app, uploads_path: str = "uploads"):
        super().__init__(app)
        self.uploads_path = uploads_path
        
        # Security headers for static files
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin"
        }
        
        # Cache headers for different file types
        self.cache_headers = {
            # Images - cache for 1 year
            'image': {
                "Cache-Control": "public, max-age=31536000, immutable",
                "Expires": self._get_expires_header(31536000)
            },
            # Other files - cache for 1 day
            'default': {
                "Cache-Control": "public, max-age=86400",
                "Expires": self._get_expires_header(86400)
            }
        }
    
    def _get_expires_header(self, max_age: int) -> str:
        """Generate Expires header value"""
        expires_time = time.time() + max_age
        return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(expires_time))
    
    def _is_static_file_request(self, path: str) -> bool:
        """Check if request is for static files"""
        return path.startswith("/uploads/") or path.startswith("/static/uploads/")
    
    def _get_file_type(self, path: str) -> str:
        """Determine file type for caching strategy"""
        ext = os.path.splitext(path)[1].lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg']:
            return 'image'
        
        return 'default'
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response"""
        for header, value in self.security_headers.items():
            response.headers[header] = value
    
    def _add_cache_headers(self, response: Response, file_type: str) -> None:
        """Add caching headers to response"""
        cache_config = self.cache_headers.get(file_type, self.cache_headers['default'])
        
        for header, value in cache_config.items():
            response.headers[header] = value
    
    def _add_cors_headers(self, response: Response) -> None:
        """Add CORS headers for static files"""
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, HEAD, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "86400"
    
    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        """Process request and add appropriate headers"""
        
        # Process the request
        response = await call_next(request)
        
        # Only modify static file responses
        if self._is_static_file_request(request.url.path):
            
            # Determine file type
            file_type = self._get_file_type(request.url.path)
            
            # Add security headers
            self._add_security_headers(response)
            
            # Add caching headers for successful responses
            if response.status_code == 200:
                self._add_cache_headers(response, file_type)
                
                # Add ETag if not present
                if "etag" not in response.headers:
                    # Simple ETag based on URL and current time (for demo)
                    etag = f'"{hash(request.url.path + str(time.time() // 3600))}"'
                    response.headers["ETag"] = etag
            
            # Add CORS headers for static files
            self._add_cors_headers(response)
            
            # Add content disposition for downloads (optional)
            if request.query_params.get("download") == "1":
                filename = os.path.basename(request.url.path)
                response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        
        return response


class StaticFileCompressionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle compression for static files
    """
    
    def __init__(self, app, min_size: int = 1024):
        super().__init__(app)
        self.min_size = min_size
        
        # File types that should be compressed
        self.compressible_types = {
            'text/css', 'text/javascript', 'application/javascript',
            'text/html', 'text/plain', 'application/json',
            'image/svg+xml'
        }
    
    def _should_compress(self, response: Response) -> bool:
        """Determine if response should be compressed"""
        
        # Check content type
        content_type = response.headers.get("content-type", "").split(";")[0]
        if content_type not in self.compressible_types:
            return False
        
        # Check content length
        content_length = response.headers.get("content-length")
        if content_length and int(content_length) < self.min_size:
            return False
        
        return True
    
    async def dispatch(self, request: Request, call_next: Callable) -> StarletteResponse:
        """Process request and add compression if appropriate"""
        
        response = await call_next(request)
        
        # Only process static file requests
        if not request.url.path.startswith("/uploads/"):
            return response
        
        # Check if client accepts gzip
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response
        
        # Check if response should be compressed
        if not self._should_compress(response):
            return response
        
        # Add compression headers (actual compression would be handled by reverse proxy)
        response.headers["Vary"] = "Accept-Encoding"
        
        return response


# Utility functions for static file handling
def get_static_file_url(file_path: str, base_url: str = "") -> str:
    """
    Generate URL for static file
    
    Args:
        file_path: Relative path from uploads directory
        base_url: Base URL (for CDN or different domain)
        
    Returns:
        str: Full URL to static file
    """
    if base_url:
        return f"{base_url.rstrip('/')}/uploads/{file_path.lstrip('/')}"
    else:
        return f"/uploads/{file_path.lstrip('/')}"


def validate_static_file_path(file_path: str, uploads_dir: str = "uploads") -> bool:
    """
    Validate that file path is safe and within uploads directory
    
    Args:
        file_path: File path to validate
        uploads_dir: Base uploads directory
        
    Returns:
        bool: True if path is safe
    """
    try:
        # Resolve absolute paths
        uploads_abs = os.path.abspath(uploads_dir)
        file_abs = os.path.abspath(os.path.join(uploads_dir, file_path))
        
        # Check if file is within uploads directory
        return file_abs.startswith(uploads_abs)
        
    except Exception:
        return False


def get_file_metadata(file_path: str) -> dict:
    """
    Get metadata for static file
    
    Args:
        file_path: Path to file
        
    Returns:
        dict: File metadata
    """
    try:
        if not os.path.exists(file_path):
            return {"exists": False}
        
        stat = os.stat(file_path)
        
        return {
            "exists": True,
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime,
            "is_file": os.path.isfile(file_path),
            "extension": os.path.splitext(file_path)[1].lower(),
            "basename": os.path.basename(file_path)
        }
        
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }