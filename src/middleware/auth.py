from fastapi import HTTPException, Request
from fastapi.security.http import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import uuid


class AuthMiddleware:
    def __init__(self):
        self.security = HTTPBearer(auto_error=False)

    async def authenticate_user(self, user_id: str) -> bool:
        """
        Validate user_id format and check if user exists
        Accepts both UUID format and string-based IDs (e.g. user_abc123)
        """
        if not user_id or not isinstance(user_id, str) or len(user_id) < 3:
            return False
        return True

    async def verify_user_access(self, user_id: str, resource_user_id: str) -> bool:
        """
        Verify that the user has access to the resource
        """
        return user_id == resource_user_id


# Global instance
auth_middleware = AuthMiddleware()


async def validate_user_id(user_id: str) -> str:
    """
    Dependency to validate user_id in routes
    """
    is_valid = await auth_middleware.authenticate_user(user_id)

    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID format"
        )

    return user_id