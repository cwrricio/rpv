import pytest

from functions.auth.ports import AuthConfigurationError, AuthenticatedUser, InvalidTokenError
from functions.auth.providers import (
    AuthConfig,
    DisabledAuthProvider,
    build_auth_provider,
    describe_auth_config,
    load_auth_config,
)
from functions.auth.tokens import parse_bearer_token


def test_authenticated_user_public_dict_omite_claims_brutas():
    user = AuthenticatedUser(
        subject="user-123",
        provider="oidc",
        email="u@example.com",
        roles=("admin",),
        claims={"raw": "secret-ish"},
    )

    assert user.to_public_dict() == {
        "subject": "user-123",
        "provider": "oidc",
        "email": "u@example.com",
        "name": None,
        "roles": ["admin"],
    }


def test_parse_bearer_token():
    assert parse_bearer_token(None) is None
    assert parse_bearer_token("Bearer abc.def") == "abc.def"


def test_parse_bearer_token_rejeita_header_malformado():
    with pytest.raises(InvalidTokenError):
        parse_bearer_token("Basic abc")


def test_disabled_provider_nao_autentica_tokens():
    provider = DisabledAuthProvider()

    assert provider.authenticate(None) is None
    assert provider.authenticate("qualquer-token") is None


def test_auth_config_default_eh_disabled():
    class Source:
        AUTH_PROVIDER = None
        AUTH_REQUIRED = "false"
        OIDC_ISSUER_URL = None
        OIDC_AUDIENCE = None
        OIDC_JWKS_URL = None

    config = load_auth_config(Source)

    assert config.provider == "disabled"
    assert config.required is False
    assert build_auth_provider(config).name == "disabled"


def test_oidc_placeholder_falha_fechado_ate_verificador_real():
    config = AuthConfig(
        provider="oidc",
        required=True,
        oidc_issuer_url="https://id.example.test/realms/poshboard",
        oidc_audience="poshboard-api",
    )
    provider = build_auth_provider(config)

    with pytest.raises(AuthConfigurationError):
        provider.authenticate("jwt-token")


def test_describe_auth_config_nao_expoe_valores_oidc():
    config = AuthConfig(
        provider="oidc",
        required=True,
        oidc_issuer_url="https://issuer.example",
        oidc_audience="aud",
        oidc_jwks_url="https://issuer.example/jwks",
    )

    description = describe_auth_config(config)

    assert description["provider"] == "oidc"
    assert description["required"] is True
    assert description["oidc"] == {
        "issuer_url_configured": True,
        "audience_configured": True,
        "jwks_url_configured": True,
    }
    assert "issuer.example" not in str(description)
