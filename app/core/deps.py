from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from regex import E
from sqlalchemy import true
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.orm import User
from ..core.security import decode_access_token
from ..config import get_settings

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub") # type: ignore
        if not user_id:
            raise exc
    except JWTError:
        raise exc

    user = db.get(User, user_id)
    if not user or not user.is_active is True:
        raise exc
    return user


def get_verified_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_verified is True:
        raise HTTPException(status_code=403, detail="Email not verified")
    return user
