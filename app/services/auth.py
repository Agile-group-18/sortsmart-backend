from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..models.orm import User, RefreshToken, EmailToken
from ..models.schemas import LoginRequest, RegisterRequest, TokenResponse
from ..core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_email_token,
)
from ..config import get_settings
from .email import send_verification_email, send_reset_email

settings = get_settings()


def _by_username_or_email(db: Session, value: str) -> User | None:
    return (
        db.query(User).filter((User.username == value) | (User.email == value)).first()
    )


async def register(db: Session, data: RegisterRequest) -> None:
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        if existing_user.is_active:
            raise HTTPException(400, "Email allready registred")
        existing_user.username = data.username
        existing_user.hashed_password = hash_password(data.password)
        existing_user.is_active = True
        existing_user.is_verified = False
        user = existing_user
        db.flush()
    else:
        if db.query(User).filter(User.username == data.username).first():
            raise HTTPException(400, "Username already taken")
        user = User(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
        )
        db.add(user)
        db.flush()

    et = EmailToken(
        user_id=user.id,
        token=create_email_token(),
        purpose="verify",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(et)
    db.commit()
    await send_verification_email(user.email, et.token)


def login(db: Session, data: LoginRequest) -> TokenResponse:
    user = _by_username_or_email(db, data.username_or_email)

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "Incorrect credentials")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    if not user.is_verified:
        raise HTTPException(403, "Email not verified - check your inbox")

    rt = RefreshToken(
        user_id=user.id,
        token=create_refresh_token(),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(rt)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        refresh_token=rt.token,
    )


def refresh(db: Session, raw_token: str) -> TokenResponse:
    rt = db.query(RefreshToken).filter(RefreshToken.token == raw_token).first()

    if not rt or rt.revoked:
        raise HTTPException(401, "Invalid refresh token")
    if rt.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(401, "Refresh token expired - please log in again")

    rt.revoked = True  # rotate: old token dies immediately
    db.flush()

    user = db.get(User, rt.user_id)

    if not user or not user.is_active:
        raise HTTPException(401, "User not found or inactive")

    new_rt = RefreshToken(
        user_id=user.id,
        token=create_refresh_token(),
        expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(new_rt)
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        refresh_token=new_rt.token,
    )


def logout(db: Session, raw_token: str) -> None:
    rt = db.query(RefreshToken).filter(RefreshToken.token == raw_token).first()
    if rt:
        rt.revoked = True
        db.commit()


def verify_email(db: Session, token: str) -> None:
    et = (
        db.query(EmailToken)
        .filter(EmailToken.token == token, EmailToken.purpose == "verify")
        .first()
    )
    if not et or et.used:
        raise HTTPException(400, "Invalid or already-used token")
    if et.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(400, "Token expired - register again")

    et.used = True
    user = db.get(User, et.user_id)
    if not user or not user.is_active:
        raise HTTPException(400, "User not found or inactive")

    user.is_verified = True
    db.commit()


async def forgot_password(db: Session, username_or_email: str) -> None:
    user = _by_username_or_email(db, username_or_email)
    if not user:
        return  # principle of least knowledge applies here!

    et = EmailToken(
        user_id=user.id,
        token=create_email_token(),
        purpose="reset",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db.add(et)
    db.commit()
    await send_reset_email(user.email, et.token)


def reset_password(db: Session, token: str, new_password: str) -> None:
    et = (
        db.query(EmailToken)
        .filter(EmailToken.token == token, EmailToken.purpose == "reset")
        .first()
    )
    if not et or et.used:
        raise HTTPException(400, "Invalid or already-used token")
    if et.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(400, "Token expired - request a new reset link")

    user = db.get(User, et.user_id)
    if not user or not user.is_active:
        raise HTTPException(400, "User not found or inactive")
    user.hashed_password = hash_password(new_password)
    et.used = True

    # Revoke every active session
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False)
    ).update({"revoked": True})
    db.commit()
