from functools import lru_cache

from fastapi import APIRouter, Depends

from functions.crud.produto_crud import ProdutoCRUD
from functions.services.produtos import build_author_product_ranking

router = APIRouter(tags=["Produtos"])


@lru_cache
def crud() -> ProdutoCRUD:
    return ProdutoCRUD()


@router.get("", summary="Listar")
@router.get("/", include_in_schema=False)
def listar(svc: ProdutoCRUD = Depends(crud)):
    return svc.list()


@router.get("/ranking", summary="Ranking de autores por número de produtos")
def ranking(svc: ProdutoCRUD = Depends(crud)):
    return build_author_product_ranking(lambda: svc.list())
