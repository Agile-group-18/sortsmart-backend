from fastapi import HTTPException
from sqlalchemy.orm import Session
from ..models.orm import User
from .email import send_disabled_email


async def disable(db: Session, user: User) -> None:
    """Disable a user account. This is a soft delete - the account can be reactivated within 90 days by contacting support or recreating the account with the same email."""
    if not user.is_active:
        raise HTTPException(400, "Account already disabled")
    user.is_active = False
    db.commit()
    await send_disabled_email(user.email)
