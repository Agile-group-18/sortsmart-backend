from pwdlib import PasswordHash
from jose import jwt
from datetime import datetime, timedelta, timezone
import secrets
from ..config import get_settings

settings = get_settings()
pwd_hash = PasswordHash.recommended()


def hash_password(plain: str) -> str:
    # TODO: generates its own salt and includes it in the hash string, so we don't need to manage salts separately
    return pwd_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_hash.verify(plain, hashed)


def create_access_token(user_id: str, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": user_id, "username": username, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def create_email_token() -> str:
    return secrets.token_urlsafe(48)
