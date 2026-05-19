import logging
import os
import resend
from ..config import get_settings

settings = get_settings()
logger = logging.getLogger("sortsmart.email")
resend.api_key = settings.resend_api_key
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(CURRENT_DIR, "..", "templates")

async def _send(to: str, subject: str, body: str) -> None:
    if settings.mail_console:
        logger.info("── EMAIL (console mode) ──────────────────────────")
        logger.info("To:      %s", to)
        logger.info("Subject: %s", subject)
        logger.info(body)
        logger.info("──────────────────────────────────────────────────")
        return


    try:
        resend.Emails.send({
            "from": f"{settings.app_name} <{settings.mail_from}>",
            "to": [to],
            "subject": subject,
            "html": body,
            
        })
        logger.info("Email sent succesfully to %s",to)
    except Exception as e:
        logger.error("Failed to send email via Resend %s",e)
        


async def send_verification_email(to: str, token: str) -> None:
    link = f"{settings.frontend_url}/verify-email?token={token}"
    email_text = (
        f"Thank you for signing up. To complete your registration and unlock all features, "
        f"please verify your email address by clicking the button below.<br><br>"
        f"This link is valid for 24 hours. If you didn't create an account, you can safely ignore this email."
    )
    try:
        with open(os.path.join(TEMPLATES_DIR, "verification_email.html"), "r", encoding="utf-8") as f:
            html_content = f.read().format(app_name=settings.app_name, link=link, text=email_text)
    except Exception as e:
        logger.warning("Could not load HTML template, using text fallback: %s", e)
        html_content = (
            f"Welcome to {settings.app_name}!<br><br>"
            f"Verify your email (valid 24 h):<br><a href='{link}'>{link}</a><br><br>"
            "If you didn't create an account, ignore this."
        )
    await _send(to, f"[{settings.app_name}] Verify your email", html_content)


async def send_reset_email(to: str, token: str) -> None:
    link = f"{settings.frontend_url}/reset-password?token={token}"
    email_text = (
        f"You requested a password reset. Click the button below to choose a new password.<br><br>"
        f"This link is valid for 15 minutes. If you didn't request this, you can safely ignore this email.<br><br>"
        f"If the button doesn't work, you can use this link:<br>"
        f"<a href='{link}' style='color: #386B21;'>{link}</a>"
    )
    try:
        with open(os.path.join(TEMPLATES_DIR, "reset_email.html"), "r", encoding="utf-8") as f:
            html_content = f.read().format(app_name=settings.app_name, link=link, text=email_text)
    except Exception as e:
        logger.warning("Could not load HTML template, using text fallback: %s", e)
        html_content = (
            f"Reset your password (valid 15 min):<br><a href='{link}'>{link}</a><br><br>"
            "If you didn't request this, ignore this email."
        )
    await _send(to, f"[{settings.app_name}] Password reset", html_content)


async def send_disabled_email(to: str) -> None:
    original_text = (
        "Thank you for being with us. Your account has been disabled as per your request. If this was a mistake or you change your mind, please recreate your account with the same email to start using our services again.\n\n"
        "As per our policy, we keep your data for 90 days in case you want to reactivate. After that, all your data will be permanently deleted. If you have any questions, feel free to contact our support. "
        "If you didn't request this, please contact support immediately."
    )
    try:
        html_text = original_text.replace("\n\n", "<br><br>")
        with open(os.path.join(TEMPLATES_DIR, "disabled_email.html"), "r", encoding="utf-8") as f:
            html_content = f.read().format(app_name=settings.app_name, text=html_text)
    except Exception as e:
        logger.warning("Could not load HTML template, using text fallback: %s", e)
        html_content = original_text.replace("\n\n", "<br><br>")
    await _send(to, f"[{settings.app_name}] Account disabled", html_content)
