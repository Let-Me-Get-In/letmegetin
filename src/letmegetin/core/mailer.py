"""Outbound mail: console in development, SMTP when ``LETMEGETIN_SMTP_HOST`` is set."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from letmegetin.config import settings

logger = logging.getLogger(__name__)


def _deliver(to: str, subject: str, body: str) -> None:
    if not settings.smtp_host:
        logger.info("mail to %s: %s", to, body)
        return
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password or "")
        smtp.send_message(message)


async def send_verification_email(to: str, token: str) -> None:
    """Send (or log) the address-confirmation link for a verification token."""
    link = f"{settings.public_base_url.rstrip('/')}/verify-email?token={token}"
    body = f"Confirm your LetMeGetIn address: {link}\n\nThis link expires in 24 hours."
    await asyncio.to_thread(_deliver, to, "Confirm your LetMeGetIn address", body)
