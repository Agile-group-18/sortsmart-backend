from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.orm import User, StatusReport
from ..models.schemas import ProfileResponse, ProfileUpdateRequest
from ..core.deps import get_current_user

from ..services import profile as svc

router = APIRouter(prefix="/profile", tags=["Profile"])


def _schema(user: User, db: Session) -> ProfileResponse:
    count = db.query(StatusReport).filter(StatusReport.user_id == user.id).count()
    return ProfileResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        is_verified=user.is_verified,
        created_at=user.created_at,
        report_count=count,
    )


@router.get("", response_model=ProfileResponse)
def get_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _schema(user, db)


@router.patch("", response_model=ProfileResponse)
def update_profile(
    body: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if body.username and body.username != user.username:
        if db.query(User).filter(User.username == body.username).first():
            raise HTTPException(400, "Username already taken")
        user.username = body.username
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    db.commit()
    db.refresh(user)
    return _schema(user, db)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    await svc.disable(db, user)
    return {
        "message": "Account disabled. If this was a mistake, please contact support or recreate your account with the same email."
    }
