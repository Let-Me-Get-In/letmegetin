"""Idempotency-Key replay for write endpoints.

The first request with a key stores its response; a retry with the same key and payload returns
that response instead of repeating the write. Reusing a key with a different payload is a 409.
"""

from __future__ import annotations

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from letmegetin.domain.accounts.entities import IdempotencyRecord
from letmegetin.infrastructure.persistence.repositories import SqlAlchemyIdempotencyRepository


async def replay(
    session: AsyncSession, user_id: int, key: str | None, request_hash: str
) -> JSONResponse | None:
    """Return the stored response, or None when this is the first attempt."""
    if not key:
        return None
    record = await SqlAlchemyIdempotencyRepository(session).get(user_id, key)
    if record is None:
        return None
    if record.request_hash != request_hash:
        raise HTTPException(
            status_code=409,
            detail="Idempotency-Key was reused with a different request",
        )
    return JSONResponse(content=record.body, status_code=record.status_code)


async def remember(
    session: AsyncSession,
    user_id: int,
    key: str | None,
    request_hash: str,
    status_code: int,
    body: dict[str, object],
) -> None:
    """Store the response for a later retry (no commit)."""
    if not key:
        return
    await SqlAlchemyIdempotencyRepository(session).add(
        IdempotencyRecord(
            user_id=user_id,
            key=key,
            request_hash=request_hash,
            status_code=status_code,
            body=body,
        )
    )
