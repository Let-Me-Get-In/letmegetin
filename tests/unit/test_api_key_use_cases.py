"""Unit tests for API-key creation, hashing and validation."""

from __future__ import annotations

import pytest

from letmegetin.application.accounts.api_keys import (
    create_api_key,
    list_api_keys,
    revoke_api_key,
)
from letmegetin.core.exceptions import DomainError
from letmegetin.core.security import generate_api_key, token_fingerprint
from letmegetin.domain.accounts.entities import ApiKey


class _Keys:
    def __init__(self) -> None:
        self.rows: list[ApiKey] = []
        self._next = 1

    async def add(self, api_key: ApiKey) -> ApiKey:
        stored = ApiKey(
            id=self._next,
            label=api_key.label,
            key_hash=api_key.key_hash,
            rpm=api_key.rpm,
            active=api_key.active,
        )
        self.rows.append(stored)
        self._next += 1
        return stored

    async def list_all(self) -> list[ApiKey]:
        return list(self.rows)

    async def get_by_hash(self, key_hash: str) -> ApiKey | None:
        return next((row for row in self.rows if row.key_hash == key_hash), None)

    async def revoke(self, key_id: int) -> ApiKey | None:
        for row in self.rows:
            if row.id == key_id:
                row.active = False
                return row
        return None


def test_generated_key_has_the_partner_prefix() -> None:
    key = generate_api_key()

    assert key.startswith("lmg_")
    assert len(key) > 30


async def test_create_stores_only_the_hash() -> None:
    keys = _Keys()

    raw, stored = await create_api_key(keys, "  Booking pilot  ", 120)

    assert raw.startswith("lmg_")
    assert stored.label == "Booking pilot"
    assert stored.rpm == 120
    assert stored.key_hash == token_fingerprint(raw)
    assert raw not in (row.key_hash for row in keys.rows)


@pytest.mark.parametrize("label,rpm", [("", 60), ("pilot", 0), ("pilot", 10_001)])
async def test_create_rejects_invalid_input(label: str, rpm: int) -> None:
    with pytest.raises(DomainError):
        await create_api_key(_Keys(), label, rpm)


async def test_list_and_revoke() -> None:
    keys = _Keys()
    _, stored = await create_api_key(keys, "pilot")

    assert await list_api_keys(keys) == [stored]
    revoked = await revoke_api_key(keys, stored.id)
    assert revoked.active is False

    with pytest.raises(DomainError):
        await revoke_api_key(keys, 999)
