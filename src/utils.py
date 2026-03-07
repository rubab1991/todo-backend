from typing import Dict, Any
import jose.jwt

def decode_jwt_token(token: str, secret: str) -> Dict[str, Any]:
    return jose.jwt.decode(token, secret, algorithms=["HS256"])
