from dataclasses import dataclass
from typing import Any, Dict, Optional

from functions.auth.ports import AuthConfigurationError, AuthProviderPort, AuthenticatedUser


@dataclass(frozen=True)
class AuthConfig:
    provider: str = "disabled"
    required: bool = False
    oidc_issuer_url: Optional[str] = None
    oidc_audience: Optional[str] = None
    oidc_jwks_url: Optional[str] = None


class DisabledAuthProvider:
    name = "disabled"

    def authenticate(self, bearer_token: Optional[str]) -> Optional[AuthenticatedUser]:
        return None


class OIDCPlaceholderProvider:
    name = "oidc"

    def __init__(self, config: AuthConfig):
        self.config = config

    def authenticate(self, bearer_token: Optional[str]) -> Optional[AuthenticatedUser]:
        if not bearer_token:
            return None
        if not self.config.oidc_issuer_url or not self.config.oidc_audience:
            raise AuthConfigurationError(
                "AUTH_PROVIDER=oidc requires OIDC_ISSUER_URL and OIDC_AUDIENCE."
            )
        raise AuthConfigurationError(
            "OIDC token verification is planned but not enabled in this POC. "
            "Add JWKS/JWT verification before protecting production routes."
        )


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _default_settings() -> Any:
    from config.settings import settings

    return settings


def load_auth_config(source: Any = None) -> AuthConfig:
    source = source or _default_settings()
    provider = (getattr(source, "AUTH_PROVIDER", "disabled") or "disabled").strip().lower()
    return AuthConfig(
        provider=provider,
        required=_as_bool(getattr(source, "AUTH_REQUIRED", False)),
        oidc_issuer_url=getattr(source, "OIDC_ISSUER_URL", None),
        oidc_audience=getattr(source, "OIDC_AUDIENCE", None),
        oidc_jwks_url=getattr(source, "OIDC_JWKS_URL", None),
    )


def build_auth_provider(config: Optional[AuthConfig] = None) -> AuthProviderPort:
    config = config or load_auth_config()
    if config.provider in {"disabled", "none", "off"}:
        return DisabledAuthProvider()
    if config.provider == "oidc":
        return OIDCPlaceholderProvider(config)
    raise AuthConfigurationError(f"Unsupported AUTH_PROVIDER: {config.provider}")


def describe_auth_config(config: Optional[AuthConfig] = None) -> Dict[str, Any]:
    config = config or load_auth_config()
    oidc_configured = bool(config.oidc_issuer_url and config.oidc_audience)
    status = "disabled" if config.provider == "disabled" else "planned"
    if config.provider == "oidc" and oidc_configured:
        status = "poc-waiting-token-verifier"
    return {
        "provider": config.provider,
        "required": config.required,
        "status": status,
        "oidc": {
            "issuer_url_configured": bool(config.oidc_issuer_url),
            "audience_configured": bool(config.oidc_audience),
            "jwks_url_configured": bool(config.oidc_jwks_url),
        },
        "firebase_auth": "not-used",
    }
