"""Application/domain errors (no FastAPI, no SQLAlchemy)."""

from __future__ import annotations


class DomainError(Exception):
    """Base class for domain errors."""


class NotFoundError(DomainError):
    """Raised when an aggregate cannot be found."""

    def __init__(self, resource: str, identifier: str) -> None:
        self.resource = resource
        self.identifier = identifier
        super().__init__(f"{resource} '{identifier}' not found")


class CategoryNotFound(NotFoundError):
    """Raised when a category slug does not exist."""

    def __init__(self, slug: str) -> None:
        super().__init__("Category", slug)
