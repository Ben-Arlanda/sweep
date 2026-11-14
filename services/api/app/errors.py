"""Domain errors raised by services.

Services know nothing about HTTP, so the same code can be called by routes today and by
agent tools later. `app.main` maps these to status codes in one place.
"""


class DomainError(Exception):
    code = "error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotInHousehold(DomainError):
    code = "not_in_household"


class AlreadyInHousehold(DomainError):
    code = "already_in_household"


class InviteInvalid(DomainError):
    code = "invite_invalid"


class PermissionDenied(DomainError):
    code = "permission_denied"


class NotFound(DomainError):
    code = "not_found"


class Conflict(DomainError):
    code = "conflict"


class LimitReached(DomainError):
    code = "limit_reached"


class IdempotencyKeyReused(DomainError):
    code = "idempotency_key_reused"


class Unavailable(DomainError):
    """A feature that depends on an outside service that isn't configured or reachable."""

    code = "unavailable"
