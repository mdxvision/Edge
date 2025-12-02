from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging
import os

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        content_security_policy: str = None,
        permissions_policy: str = None,
        trusted_proxies: list = None
    ):
        super().__init__(app)
        
        self.csp = content_security_policy or (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        
        self.permissions_policy = permissions_policy or (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )
        
        self.trusted_proxies = trusted_proxies or []
        self.force_https = os.environ.get("FORCE_HTTPS", "false").lower() == "true"
    
    def _is_https(self, request: Request) -> bool:
        if request.url.scheme == "https":
            return True
        
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "").lower()
        if forwarded_proto == "https":
            return True
        
        return self.force_https
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = self.permissions_policy
        
        if not request.url.path.startswith("/docs") and not request.url.path.startswith("/openapi"):
            response.headers["Content-Security-Policy"] = self.csp
        
        if self._is_https(request):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        
        return response
