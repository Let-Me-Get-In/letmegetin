"""Unit tests for password hashing and signed tokens."""

from __future__ import annotations

import pytest

from letmegetin.core import security
from letmegetin.core.exceptions import InvalidToken


def test_password_hash_roundtrip() -> None:
    stored = security.hash_password("correct horse battery")

    assert stored.startswith("scrypt$")
    assert security.verify_password("correct horse battery", stored)
    assert not security.verify_password("wrong", stored)


@pytest.mark.parametrize("stored", ["", "plain", "bcrypt$aa$bb", "scrypt$not-base64$zz"])
def test_verify_password_rejects_malformed_hashes(stored: str) -> None:
    assert security.verify_password("x", stored) is False


def test_token_roundtrip() -> None:
    token = security.create_token(42, "user", "access", 60)

    payload = security.decode_token(token, "access")

    assert (payload.user_id, payload.role) == (42, "user")


def test_token_rejects_wrong_kind() -> None:
    token = security.create_token(42, "user", "refresh", 60)

    with pytest.raises(InvalidToken):
        security.decode_token(token, "access")


def test_token_rejects_expired() -> None:
    token = security.create_token(42, "user", "access", -10)

    with pytest.raises(InvalidToken):
        security.decode_token(token, "access")


def test_token_rejects_tampering() -> None:
    token = security.create_token(42, "user", "access", 60)
    header, payload, signature = token.split(".")
    tampered = ("A" if payload[0] != "A" else "B") + payload[1:]

    with pytest.raises(InvalidToken):
        security.decode_token(f"{header}.{tampered}.{signature}", "access")
