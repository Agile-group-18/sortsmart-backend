from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..models.orm import User, EmailToken
from .email import send_disabled_email, send_verification_email
from ..core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_email_token,
)


async def update_email(db: Session, user: User, new_email: str) -> None:
    """Update a user's email address. Marks the user as unverified and sends a new verification email to the new address."""
    if db.query(User).filter(User.email == new_email).first():
        raise HTTPException(400, "Email already registered")

    user.email = new_email
    user.is_verified = False

    et = EmailToken(
        user_id=user.id,
        token=create_email_token(),
        purpose="verify",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add(et)
    db.commit()
    await send_verification_email(user.email, et.token)


async def disable(db: Session, user: User) -> None:
    """Disable a user account. This is a soft delete - the account can be reactivated within 90 days by contacting support or recreating the account with the same email."""
    if not user.is_active:
        raise HTTPException(400, "Account already disabled")
    user.is_active = False
    db.commit()
    await send_disabled_email(user.email)
