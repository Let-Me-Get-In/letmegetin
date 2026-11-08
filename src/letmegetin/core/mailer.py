"""Outbound mail: console in development, SMTP when ``LETMEGETIN_SMTP_HOST`` is set."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.message import EmailMessage

from letmegetin.config import settings

logger = logging.getLogger(__name__)

_SMTP_TIMEOUT_SECONDS = 15
# The display name is what the reader sees in the inbox; a bare address reads as
# transactional noise and gets filtered as such.
_FROM_NAME = "LetMeGetIn"

# The web app's own palette, so the email does not look foreign to the product.
_PAPER = "#f7f4ec"
_CARD = "#ffffff"
_INK = "#18211c"
_MUTED = "#5d6a61"
_LINE = "#d8ddd4"
_ACCENT = "#1f6f4a"
_ACCENT_SOFT = "#e2efe6"
_FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _text(link: str) -> str:
    """Plain-text part: readable everywhere, with the address spelled out."""
    return (
        "Confirmez votre adresse\n\n"
        "Un clic et votre compte LetMeGetIn est actif.\n\n"
        f"Confirmer mon adresse : {link}\n\n"
        "Ce lien expire dans 24 heures. Si vous n'avez pas créé de compte, "
        "ignorez cet email.\n\n"
        "— LetMeGetIn\n"
        "Le guide collaboratif des lieux accessibles."
    )


def _html(link: str) -> str:
    """One inline-styled card; table layout and inline CSS only, no external asset."""
    safe = _escape(link)
    return f"""<!doctype html>
<html lang="fr" style="color-scheme:light">
<head><meta charset="utf-8"><meta name="color-scheme" content="light"></head>
<body style="margin:0;padding:28px 16px;background:{_PAPER}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
 style="max-width:520px;margin:0 auto;background:{_CARD};border:1px solid {_LINE};
 border-radius:12px;overflow:hidden">
<tr><td style="padding:26px 28px 0;font:600 15px/1.2 {_FONT};color:{_INK};
 letter-spacing:-0.01em">LetMeGet<span style="font-weight:400;color:{_ACCENT}">In</span></td></tr>
<tr><td style="padding:16px 28px 0">
<div style="height:3px;width:44px;background:{_ACCENT};border-radius:2px"></div></td></tr>
<tr><td style="padding:20px 28px 0;font:16px/1.6 {_FONT};color:{_INK}">
<h1 style="margin:0 0 12px;font-size:25px;line-height:1.2;letter-spacing:-0.02em;
 font-weight:650">Confirmez votre adresse</h1>
<p style="margin:0 0 22px">Un clic et votre compte LetMeGetIn est actif.</p>
<p style="margin:0 0 26px"><a href="{safe}"
 style="display:inline-block;padding:13px 22px;border-radius:999px;background:{_ACCENT};
 color:#ffffff;font-weight:600;text-decoration:none">Confirmer mon adresse</a></p>
<p style="margin:0 0 6px;font-size:13px;color:{_MUTED}">Si le bouton ne fonctionne pas,
 ouvrez cette adresse :</p>
<p style="margin:0 0 26px;font-size:13px;word-break:break-all">
<a href="{safe}" style="color:{_INK};text-decoration:underline;
 text-underline-offset:2px">{safe}</a></p>
<p style="margin:0 0 26px;padding:14px 16px;border-radius:8px;background:{_ACCENT_SOFT};
 font-size:13px;color:{_INK}">Ce lien expire dans 24 heures. Si vous n'avez pas créé de
 compte, ignorez cet email.</p></td></tr>
<tr><td style="padding:18px 28px 24px;border-top:1px solid {_LINE};font:12px/1.5 {_FONT};
 color:{_MUTED}">Le guide collaboratif des lieux accessibles. Vous recevez cet email
 parce qu'un compte a été créé avec cette adresse.</td></tr>
</table></body></html>"""


def _deliver(to: str, subject: str, link: str) -> None:
    if not settings.smtp_host:
        logger.info("mail to %s: %s", to, _text(link))
        return
    message = EmailMessage()
    message["From"] = f"{_FROM_NAME} <{settings.smtp_from}>"
    message["To"] = to
    message["Subject"] = subject
    message.set_content(_text(link))
    message.add_alternative(_html(link), subtype="html")
    with smtplib.SMTP(
        settings.smtp_host, settings.smtp_port, timeout=_SMTP_TIMEOUT_SECONDS
    ) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password or "")
        smtp.send_message(message)


async def send_verification_email(to: str, token: str) -> None:
    """Send (or log) the address-confirmation link for a verification token."""
    link = f"{settings.public_base_url.rstrip('/')}/verify?token={token}"
    await asyncio.to_thread(_deliver, to, "Confirmez votre adresse LetMeGetIn", link)
