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


class ReviewNotFound(NotFoundError):
    """Raised when a review id does not exist."""

    def __init__(self, review_id: int) -> None:
        super().__init__("Review", str(review_id))


class CategoryAlreadyExists(DomainError):
    """Raised when adding a category whose slug is already taken."""

    def __init__(self, slug: str) -> None:
        super().__init__(f"Category '{slug}' already exists")


class LabelError(DomainError):
    """Raised when label input cannot be parsed or names an unsupported locale."""


class InvalidToken(DomainError):
    """Raised when a bearer or refresh token is malformed, expired or of the wrong kind."""


class InvalidCredentials(DomainError):
    """Raised when an email/password pair does not match an account."""


class EmailAlreadyUsed(DomainError):
    """Raised when registering an email that already has an account."""

    def __init__(self, email: str) -> None:
        super().__init__(f"Email '{email}' already has an account")
