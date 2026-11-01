"""Optional Sentry error tracking, with PII scrubbing."""

from __future__ import annotations

import logging
import re
from typing import Any

import sentry_sdk

from letmegetin.config import settings

logger = logging.getLogger(__name__)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _scrub(value: Any) -> Any:
    if isinstance(value, str):
        return _EMAIL.sub("[redacted-email]", value)
    if isinstance(value, dict):
        return {key: _scrub(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    return value


def before_send(event: Any, hint: Any) -> Any:
    """Drop the whole request (bodies, headers, cookies) and redact emails."""
    event.pop("request", None)
    return _scrub(event)


def init_sentry() -> None:
    """Initialise Sentry only when a DSN is configured."""
    if not settings.sentry_dsn:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        release=settings.git_sha,
        traces_sample_rate=0.1,
        send_default_pii=False,
        before_send=before_send,
    )
    logger.info("Sentry initialised (release=%s)", settings.git_sha)
