"""Password hashing and HS256 tokens, standard library only.

Passwords use scrypt with a per-password salt. Tokens are compact JWTs signed with HMAC-SHA256;
only the `sub`, `role`, `typ`, `iat` and `exp` claims are used.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from letmegetin.config import settings
from letmegetin.core.exceptions import InvalidToken

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    """Hash a password with scrypt and a random salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_DKLEN
    )
    return f"scrypt${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored scrypt hash in constant time."""
    try:
        scheme, salt, digest = stored.split("$")
    except ValueError:
        return False
    if scheme != "scrypt":
        return False
    try:
        expected = _unb64(digest)
        computed = hashlib.scrypt(
            password.encode(),
            salt=_unb64(salt),
            n=_SCRYPT_N,
            r=_SCRYPT_R,
            p=_SCRYPT_P,
            dklen=_DKLEN,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(computed, expected)


@dataclass
class TokenPayload:
    """The claims the API relies on."""

    user_id: int
    role: str


def _sign(signing_input: bytes) -> bytes:
    return hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()


def create_token(user_id: int, role: str, kind: str, ttl: int) -> str:
    """Issue a signed token of the given kind (`access` or `refresh`)."""
    now = int(time.time())
    header = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    claims = {"sub": str(user_id), "role": role, "typ": kind, "iat": now, "exp": now + ttl}
    payload = _b64(json.dumps(claims, separators=(",", ":")).encode())
    signature = _b64(_sign(f"{header}.{payload}".encode()))
    return f"{header}.{payload}.{signature}"


def decode_token(token: str, kind: str) -> TokenPayload:
    """Verify a token's signature, expiry and kind; raise ``InvalidToken`` otherwise."""
    try:
        header, payload, signature = token.split(".")
        expected = _sign(f"{header}.{payload}".encode())
        if not hmac.compare_digest(expected, _unb64(signature)):
            raise InvalidToken()
        claims = json.loads(_unb64(payload))
        if claims.get("typ") != kind or int(claims.get("exp", 0)) < int(time.time()):
            raise InvalidToken()
        return TokenPayload(user_id=int(claims["sub"]), role=str(claims.get("role", "user")))
    except InvalidToken:
        raise
    except (ValueError, TypeError, KeyError):
        raise InvalidToken() from None
