from typing import Optional

from functions.auth.ports import InvalidTokenError


def parse_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None

    parts = authorization.strip().split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise InvalidTokenError("Expected Authorization: Bearer <token>.")
    return parts[1]
