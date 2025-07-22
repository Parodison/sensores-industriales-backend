import jwt
from conf import env
from datetime import datetime, timedelta, timezone
from typing import TypedDict


class JWTPayload(TypedDict):
    exp: int
    iat: int
    type: str
    user_id: int
    email: str
    role: str

class Authentication:
    def __init__(self):
        self.secret_key = env.secret_key
        self.algorithm = "HS256"
        self.access_token_expiration = timedelta(hours=1)
        self.refresh_token_expiration = timedelta(days=30)

    def create_refresh_token(self, data: dict) -> str:
        payload = {
            "exp": datetime.now(timezone.utc) + self.refresh_token_expiration,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
            **data,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_access_token(self, data: dict) -> str:
        payload = {
            "exp": datetime.now(timezone.utc) + self.access_token_expiration,
            "iat": datetime.now(timezone.utc),
            "type": "access",
            **data,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_access_token(self, access_token: str) -> JWTPayload | None:
        try:
            payload = jwt.decode(access_token, self.secret_key, algorithms=[self.algorithm])
            
            return payload
        
        except Exception as e:
            print(f"Error al validar el access token: {e}")
            return None

auth = Authentication()