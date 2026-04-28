import logging
from ..config import get_settings

settings = get_settings()
logger = logging.getLogger("sortsmart.email")


async def _send(to: str, subject: str, body: str) -> None:
    if settings.mail_console:
        logger.info("── EMAIL (console mode) ──────────────────────────")
        logger.info("To:      %s", to)
        logger.info("Subject: %s", subject)
        logger.info(body)
        logger.info("──────────────────────────────────────────────────")
        return

    from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
    from pydantic import NameEmail

    conf = ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from,
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_STARTTLS=settings.mail_starttls,
        MAIL_SSL_TLS=settings.mail_ssl_tls,
        USE_CREDENTIALS=True,
    )
    msg = MessageSchema(
        subject=subject,
        recipients=[NameEmail(name=to, email=to)],
        body=body,
        subtype=MessageType.plain,
    )
    await FastMail(conf).send_message(msg)


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
