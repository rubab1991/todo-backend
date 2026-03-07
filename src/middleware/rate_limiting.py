import time
from typing import Dict
from collections import defaultdict
from fastapi import Request, HTTPException
from ..config import settings


class RateLimiter:
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if the request from the given identifier is allowed
        """
        now = time.time()
        # Clean old requests (older than 1 minute)
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < 60
        ]

        # Check if the number of requests is within the limit
        if len(self.requests[identifier]) < self.requests_per_minute:
            self.requests[identifier].append(now)
            return True

        return False


# Global rate limiter instance
rate_limiter = RateLimiter(requests_per_minute=60)


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0]

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    return request.client.host


async def rate_limit_middleware(request: Request, call_next):
    """
    Middleware to implement rate limiting
    """
    client_ip = get_client_ip(request)

    # For API endpoints, apply rate limiting
    if request.url.path.startswith('/api/'):
        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )

    response = await call_next(request)
    return response


def rate_limit_dependency():
    """
    Dependency for rate limiting on specific endpoints
    """
    def rate_limit_check(request: Request):
        client_ip = get_client_ip(request)

        if not rate_limiter.is_allowed(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )

        return True

    return rate_limit_check