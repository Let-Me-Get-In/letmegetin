"""Use cases: partner API keys (create once, list, revoke)."""

from __future__ import annotations

from letmegetin.core.exceptions import DomainError
from letmegetin.core.security import generate_api_key, token_fingerprint
from letmegetin.domain.accounts.entities import ApiKey
from letmegetin.domain.accounts.repositories import ApiKeyRepository

MIN_RPM = 1
MAX_RPM = 10_000


async def create_api_key(keys: ApiKeyRepository, label: str, rpm: int = 60) -> tuple[str, ApiKey]:
    """Return the raw key (shown once) and the stored record."""
    clean_label = label.strip()
    if not clean_label:
        raise DomainError("label is required")
    if not MIN_RPM <= rpm <= MAX_RPM:
        raise DomainError(f"rpm must be between {MIN_RPM} and {MAX_RPM}")
    raw = generate_api_key()
    stored = await keys.add(
        ApiKey(id=0, label=clean_label, key_hash=token_fingerprint(raw), rpm=rpm)
    )
    return raw, stored


async def list_api_keys(keys: ApiKeyRepository) -> list[ApiKey]:
    return await keys.list_all()


async def revoke_api_key(keys: ApiKeyRepository, key_id: int) -> ApiKey:
    revoked = await keys.revoke(key_id)
    if revoked is None:
        raise DomainError(f"API key {key_id} not found")
    return revoked
