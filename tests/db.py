"""Real-PostGIS plumbing shared by the integration and functional suites."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from letmegetin.config import settings

# NullPool: every CLI call runs its own event loop via asyncio.run, and the
# TestClient drives another one; a pooled asyncpg connection cannot cross loops.
engine = create_async_engine(settings.database_url, poolclass=NullPool)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def run[T](coro: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coro)


async def _database_ready(*tables: str) -> bool:
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
            for table in tables:
                if await session.scalar(text("SELECT to_regclass(:name)"), {"name": table}) is None:
                    return False
        return True
    except Exception:  # noqa: BLE001 - any connection failure means "unavailable"
        return False


def require_database(*tables: str) -> None:
    if not run(_database_ready(*tables)):
        pytest.skip(f"database or {', '.join(tables) or 'schema'} unavailable")


def execute(statement: str, params: dict[str, Any] | None = None) -> None:
    async def _execute() -> None:
        async with SessionLocal() as session:
            await session.execute(text(statement), params or {})
            await session.commit()

    run(_execute())


def scalar(statement: str, params: dict[str, Any] | None = None) -> Any:
    async def _scalar() -> Any:
        async with SessionLocal() as session:
            value = await session.scalar(text(statement), params or {})
            await session.commit()
            return value

    return run(_scalar())


def row(statement: str, params: dict[str, Any] | None = None) -> Any:
    async def _row() -> Any:
        async with SessionLocal() as session:
            value = (await session.execute(text(statement), params or {})).one()
            await session.commit()
            return value

    return run(_row())


def rows(statement: str, params: dict[str, Any] | None = None) -> list[Any]:
    async def _rows() -> list[Any]:
        async with SessionLocal() as session:
            result = await session.execute(text(statement), params or {})
            return list(result)

    return run(_rows())
