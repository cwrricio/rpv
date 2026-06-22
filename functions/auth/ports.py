from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol, Tuple, runtime_checkable


@dataclass(frozen=True)
class AuthenticatedUser:
    """Normalized user identity exposed by auth adapters."""

    subject: str
    provider: str
    email: Optional[str] = None
    name: Optional[str] = None
    roles: Tuple[str, ...] = ()
    claims: Dict[str, Any] = field(default_factory=dict)

    def to_public_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "provider": self.provider,
            "email": self.email,
            "name": self.name,
            "roles": list(self.roles),
        }


class AuthError(Exception):
    """Base error for authentication failures."""


class AuthConfigurationError(AuthError):
    """Raised when a provider was selected but is not ready to verify tokens."""


class InvalidTokenError(AuthError):
    """Raised when an Authorization header or token is invalid."""


@runtime_checkable
class AuthProviderPort(Protocol):
    """Provider-independent authentication port."""

    name: str

    def authenticate(self, bearer_token: Optional[str]) -> Optional[AuthenticatedUser]:
        """Return a normalized user or None when no authenticated identity exists."""
        ...
