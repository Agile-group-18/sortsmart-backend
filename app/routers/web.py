from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from fastapi import Depends
from ..database import get_db
from ..services import auth as svc

router = APIRouter(tags=["Web"])

_APP_STORE_URL = "#"
_PLAY_STORE_URL = "#"


def _page(title: str, message: str, success: bool) -> str:
    color = "#2e7d32" if success else "#c62828"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} - SortSmart</title>
  <style>
    body {{ font-family: sans-serif; display: flex; justify-content: center;
            align-items: center; min-height: 100vh; margin: 0; background: #f5f5f5; }}
    .card {{ background: white; border-radius: 12px; padding: 2rem;
             max-width: 400px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,.1); }}
    h1 {{ color: {color}; }}
    a.btn {{ display: inline-block; margin: .5rem; padding: .75rem 1.5rem;
             border-radius: 8px; background: #1b5e20; color: white;
             text-decoration: none; font-weight: bold; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{title}</h1>
    <p>{message}</p>
    <a class="btn" href="{_APP_STORE_URL}">Download on App Store</a>
    <a class="btn" href="{_PLAY_STORE_URL}">Get on Google Play</a>
  </div>
</body>
</html>"""


@router.get("/verify-email", response_class=HTMLResponse)
def verify_email_web(token: str, db: Session = Depends(get_db)):
    try:
        svc.verify_email(db, token)
        return _page(
            "Email verified ✓",
            "Your account is verified. Open SortSmart to log in.",
            True,
        )
    except Exception as e:
        return _page(
            "Verification failed", str(e.detail if hasattr(e, "detail") else e), False  # type: ignore , FastAPI HTTPExceptions have a .detail attribute, but other exceptions might not
        )


@router.get("/reset-password", response_class=HTMLResponse)
def reset_password_web(token: str):
    # Just deep-links back to the app with the token
    # or handle it in the frontend if opened in a browser?
    # TODO: discuss this with team
    return _page(
        "Reset your password",
        "Open SortSmart to set your new password, or click your reset link again from the app.",
        True,
    )
