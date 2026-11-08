from __future__ import annotations

import asyncio
import logging

import pytest

from letmegetin.config import settings
from letmegetin.core import mailer


def test_verification_link_points_at_the_verify_page(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(settings, "smtp_host", None)
    monkeypatch.setattr(settings, "public_base_url", "https://app.example.org/")

    with caplog.at_level(logging.INFO):
        asyncio.run(mailer.send_verification_email("user@example.org", "tok123"))

    assert "https://app.example.org/verify?token=tok123" in caplog.text
    assert "/verify-email?" not in caplog.text


def test_parts_share_the_link_and_the_html_is_escaped() -> None:
    link = "https://app.example.org/verify?token=a&b=<c>"

    assert link in mailer._text(link)
    assert "token=a&amp;b=&lt;c&gt;" in mailer._html(link)
