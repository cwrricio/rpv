from typing import Optional

from fastapi import Header, HTTPException, status

from functions.auth.ports import AuthConfigurationError, AuthError, AuthenticatedUser, InvalidTokenError
from functions.auth.providers import build_auth_provider, load_auth_config
from functions.auth.tokens import parse_bearer_token


def authenticate_authorization_header(
    authorization: Optional[str],
    *,
    required: Optional[bool] = None,
) -> Optional[AuthenticatedUser]:
    config = load_auth_config()
    should_require = config.required if required is None else required

    try:
        token = parse_bearer_token(authorization)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    if should_require and not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    try:
        user = build_auth_provider(config).authenticate(token)
    except AuthConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    if should_require and user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user


def optional_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[AuthenticatedUser]:
    return authenticate_authorization_header(authorization, required=False)


def required_user(
    authorization: Optional[str] = Header(default=None),
) -> AuthenticatedUser:
    user = authenticate_authorization_header(authorization, required=True)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    return user
