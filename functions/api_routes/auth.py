from typing import Optional

from fastapi import APIRouter, Header

from functions.auth.dependencies import authenticate_authorization_header
from functions.auth.providers import describe_auth_config

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/config", summary="Expor configuracao de autenticacao sem segredos")
def auth_config():
    return describe_auth_config()


@router.get("/me", summary="Inspecionar usuario autenticado quando auth estiver habilitada")
def auth_me(authorization: Optional[str] = Header(default=None)):
    user = authenticate_authorization_header(authorization, required=False)
    if user is None:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user.to_public_dict()}
