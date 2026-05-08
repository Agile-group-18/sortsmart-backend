import logging
import resend
from ..config import get_settings

settings = get_settings()
logger = logging.getLogger("sortsmart.email")
resend.api_key = settings.resend_api_key

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
            "text": body,
            "html": f"<p>{body}<p>"
        })
        logger.info("Email sent succesfully to %s",to)
    except Exception as e:
        logger.error("Failed to send email via Resend %s",e)
        


async def send_verification_email(to: str, token: str) -> None:
    link = f"{settings.frontend_url}/verify-email?token={token}"
    await _send(
        to,
        f"[{settings.app_name}] Verify your email",
        f"Welcome to {settings.app_name}!\n\n"
        f"Verify your email (valid 24 h):\n{link}\n\n"
        "If you didn't create an account, ignore this.",
    )


async def send_reset_email(to: str, token: str) -> None:
    link = f"{settings.frontend_url}/reset-password?token={token}"
    await _send(
        to,
        f"[{settings.app_name}] Password reset",
        f"Reset your password (valid 15 min):\n{link}\n\n"
        "If you didn't request this, ignore this email.",
    )


async def send_disabled_email(to: str) -> None:
    await _send(
        to,
        f"[{settings.app_name}] Account disabled",
        "Thank you for being with us. Your account has been disabled as per your request. If this was a mistake or you change your mind, please recreate your account with the same email to start using our services again.\n\n"
        "As per our policy, we keep your data for 90 days in case you want to reactivate. After that, all your data will be permanently deleted. If you have any questions, feel free to contact our support."
        "If you didn't request this, please contact support immediately.",
    )
