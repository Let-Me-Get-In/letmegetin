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


class CriterionNotFound(NotFoundError):
    """Raised when a criterion slug does not exist."""

    def __init__(self, slug: str) -> None:
        super().__init__("Criterion", slug)


class VocabularyNotFound(NotFoundError):
    """Raised when a vocabulary slug does not exist."""

    def __init__(self, slug: str) -> None:
        super().__init__("Vocabulary entry", slug)


class PlaceNotFound(NotFoundError):
    """Raised when a place slug does not exist."""

    def __init__(self, slug: str) -> None:
        super().__init__("Place", slug)


class CategoryAlreadyExists(DomainError):
    """Raised when adding a category whose slug is already taken."""

    def __init__(self, slug: str) -> None:
        super().__init__(f"Category '{slug}' already exists")


class LabelError(DomainError):
    """Raised when label input cannot be parsed or names an unsupported locale."""
