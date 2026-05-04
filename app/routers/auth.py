from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..database import get_db
from ..models.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from ..services import auth as svc

router = APIRouter(prefix="/auth", tags=["Auth"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("3/2minutes")
async def register(
    request: Request, body: RegisterRequest, db: Session = Depends(get_db)
):
    await svc.register(db, body)
    return {"message": "Account created - check your email to verify"}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/15minutes")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    return svc.login(db, body)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    return svc.refresh(db, body.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    svc.logout(db, body.refresh_token)


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    svc.verify_email(db, token)
    return {"message": "Email verified - you can now log in"}


@router.post("/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(
    request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    await svc.forgot_password(db, body.username_or_email)
    return {"message": "If that account exists, a reset email has been sent"}


@router.post("/reset-password")
def reset_password(body: ResetPasswordRequest, db: Session = Depends(get_db)):
    svc.reset_password(db, body.token, body.new_password)
    return {"message": "Password updated - please log in again"}
