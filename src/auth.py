from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jose.jwt
from .config import settings

security = HTTPBearer()

def decode_jwt_token(token: str, secret: str):
    try:
        return jose.jwt.decode(token, secret, algorithms=["HS256"])
    except jose.JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    secret = settings.better_auth_secret
    if not secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")
    payload = decode_jwt_token(token, secret)
    user_id = payload.get("userId") or payload.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user id")
    return str(user_id)


async def get_current_user_info(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Get both user ID and email from the token"""
    token = credentials.credentials
    secret = settings.better_auth_secret
    if not secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")
    payload = decode_jwt_token(token, secret)
    user_id = payload.get("userId") or payload.get("id") or payload.get("sub")
    email = payload.get("email")

    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user id")

    return {"user_id": str(user_id), "email": email}


async def verify_user_id_match(request: Request, user_id_from_token: str = Depends(get_current_user_id)) -> str:
    path_user_id = request.path_params.get("user_id")
    if not path_user_id:
        raise HTTPException(status_code=400, detail="Missing user_id in path")
    if path_user_id != user_id_from_token:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return user_id_from_token


async def verify_user_id_match_with_email(request: Request, user_info: dict = Depends(get_current_user_info)) -> tuple:
    """
    Verify that the user ID in the token matches the user ID in the path,
    and return both user_id and email
    """
    path_user_id = request.path_params.get("user_id")
    if not path_user_id:
        raise HTTPException(status_code=400, detail="Missing user_id in path")
    if path_user_id != user_info["user_id"]:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return user_info["user_id"], user_info["email"]
