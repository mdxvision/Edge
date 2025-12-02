from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger(__name__)

MAX_TRACKED_IPS = 10000


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
        exempt_paths: list = None
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.exempt_paths = exempt_paths or ["/health", "/docs", "/openapi.json", "/"]
        
        self.minute_requests: Dict[str, List[float]] = {}
        self.hour_requests: Dict[str, List[float]] = {}
        self.burst_tracker: Dict[str, Tuple[float, int]] = {}
        self._last_cleanup = time.time()
    
    def _get_client_ip(self, request: Request) -> str:
        if request.client and request.client.host:
            return request.client.host
        
        return "unknown"
    
    def _is_exempt(self, path: str) -> bool:
        return any(path.startswith(exempt) for exempt in self.exempt_paths)
    
    def _cleanup_all(self):
        now = time.time()
        
        if now - self._last_cleanup < 60:
            return
        
        self._last_cleanup = now
        minute_ago = now - 60
        hour_ago = now - 3600
        
        for ip in list(self.minute_requests.keys()):
            self.minute_requests[ip] = [t for t in self.minute_requests[ip] if t > minute_ago]
            if not self.minute_requests[ip]:
                del self.minute_requests[ip]
        
        for ip in list(self.hour_requests.keys()):
            self.hour_requests[ip] = [t for t in self.hour_requests[ip] if t > hour_ago]
            if not self.hour_requests[ip]:
                del self.hour_requests[ip]
        
        for ip in list(self.burst_tracker.keys()):
            last_time, _ = self.burst_tracker[ip]
            if now - last_time > 10:
                del self.burst_tracker[ip]
        
        if len(self.minute_requests) > MAX_TRACKED_IPS:
            oldest_ips = sorted(self.minute_requests.keys(), 
                               key=lambda ip: min(self.minute_requests[ip]) if self.minute_requests[ip] else 0)
            for ip in oldest_ips[:len(self.minute_requests) - MAX_TRACKED_IPS]:
                del self.minute_requests[ip]
    
    def _cleanup_old_requests(self, client_ip: str):
        now = time.time()
        minute_ago = now - 60
        hour_ago = now - 3600
        
        if client_ip in self.minute_requests:
            self.minute_requests[client_ip] = [
                t for t in self.minute_requests[client_ip] if t > minute_ago
            ]
        
        if client_ip in self.hour_requests:
            self.hour_requests[client_ip] = [
                t for t in self.hour_requests[client_ip] if t > hour_ago
            ]
    
    def _check_burst(self, client_ip: str) -> bool:
        now = time.time()
        
        if client_ip in self.burst_tracker:
            last_time, count = self.burst_tracker[client_ip]
            if now - last_time < 1:
                if count >= self.burst_limit:
                    return False
                self.burst_tracker[client_ip] = (last_time, count + 1)
            else:
                self.burst_tracker[client_ip] = (now, 1)
        else:
            self.burst_tracker[client_ip] = (now, 1)
        
        return True
    
    async def dispatch(self, request: Request, call_next):
        if self._is_exempt(request.url.path):
            return await call_next(request)
        
        self._cleanup_all()
        
        client_ip = self._get_client_ip(request)
        now = time.time()
        
        self._cleanup_old_requests(client_ip)
        
        if not self._check_burst(client_ip):
            logger.warning(f"Burst limit exceeded for {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after": 1
                },
                headers={"Retry-After": "1"}
            )
        
        minute_count = len(self.minute_requests.get(client_ip, []))
        if minute_count >= self.requests_per_minute:
            logger.warning(f"Minute rate limit exceeded for {client_ip}: {minute_count} requests")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Too many requests per minute.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        hour_count = len(self.hour_requests.get(client_ip, []))
        if hour_count >= self.requests_per_hour:
            logger.warning(f"Hourly rate limit exceeded for {client_ip}: {hour_count} requests")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded. Too many requests per hour.",
                    "retry_after": 3600
                },
                headers={"Retry-After": "3600"}
            )
        
        if client_ip not in self.minute_requests:
            self.minute_requests[client_ip] = []
        if client_ip not in self.hour_requests:
            self.hour_requests[client_ip] = []
        
        self.minute_requests[client_ip].append(now)
        self.hour_requests[client_ip].append(now)
        
        response = await call_next(request)
        
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.minute_requests.get(client_ip, []))
        )
        
        return response


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        login_attempts_per_minute: int = 5,
        register_attempts_per_hour: int = 10
    ):
        super().__init__(app)
        self.login_attempts_per_minute = login_attempts_per_minute
        self.register_attempts_per_hour = register_attempts_per_hour
        
        self.login_attempts: Dict[str, List[float]] = {}
        self.register_attempts: Dict[str, List[float]] = {}
        self._last_cleanup = time.time()
    
    def _get_client_ip(self, request: Request) -> str:
        if request.client and request.client.host:
            return request.client.host
        return "unknown"
    
    def _cleanup_all(self):
        now = time.time()
        
        if now - self._last_cleanup < 60:
            return
        
        self._last_cleanup = now
        minute_ago = now - 60
        hour_ago = now - 3600
        
        for ip in list(self.login_attempts.keys()):
            self.login_attempts[ip] = [t for t in self.login_attempts[ip] if t > minute_ago]
            if not self.login_attempts[ip]:
                del self.login_attempts[ip]
        
        for ip in list(self.register_attempts.keys()):
            self.register_attempts[ip] = [t for t in self.register_attempts[ip] if t > hour_ago]
            if not self.register_attempts[ip]:
                del self.register_attempts[ip]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        
        if method != "POST":
            return await call_next(request)
        
        self._cleanup_all()
        
        client_ip = self._get_client_ip(request)
        now = time.time()
        
        if path == "/auth/login":
            minute_ago = now - 60
            if client_ip in self.login_attempts:
                self.login_attempts[client_ip] = [
                    t for t in self.login_attempts[client_ip] if t > minute_ago
                ]
            
            if len(self.login_attempts.get(client_ip, [])) >= self.login_attempts_per_minute:
                logger.warning(f"Login rate limit exceeded for {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many login attempts. Please try again later.",
                        "retry_after": 60
                    },
                    headers={"Retry-After": "60"}
                )
            
            if client_ip not in self.login_attempts:
                self.login_attempts[client_ip] = []
            self.login_attempts[client_ip].append(now)
        
        elif path == "/auth/register":
            hour_ago = now - 3600
            if client_ip in self.register_attempts:
                self.register_attempts[client_ip] = [
                    t for t in self.register_attempts[client_ip] if t > hour_ago
                ]
            
            if len(self.register_attempts.get(client_ip, [])) >= self.register_attempts_per_hour:
                logger.warning(f"Registration rate limit exceeded for {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Too many registration attempts. Please try again later.",
                        "retry_after": 3600
                    },
                    headers={"Retry-After": "3600"}
                )
            
            if client_ip not in self.register_attempts:
                self.register_attempts[client_ip] = []
            self.register_attempts[client_ip].append(now)
        
        return await call_next(request)
