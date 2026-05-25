from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from functions.repositories.linha_crud import LinhaCRUD

router = APIRouter(tags=["Linhas de Pesquisa"])


@lru_cache
def crud() -> LinhaCRUD:
    return LinhaCRUD()


@router.post("", status_code=201, summary="Criar")
@router.post("/", status_code=201, include_in_schema=False)
def criar(body: dict, svc: LinhaCRUD = Depends(crud)):
    return svc.create(body)


@router.get("", summary="Listar")
@router.get("/", include_in_schema=False)
def listar(svc: LinhaCRUD = Depends(crud)):
    return svc.list()


@router.get("/{id}", summary="Obter")
def obter(id: str, svc: LinhaCRUD = Depends(crud)):
    item = svc.get(id)
    if not item:
        raise HTTPException(404, "Linha não encontrada")
    return item


@router.patch("/{id}", summary="Atualizar")
def atualizar(id: str, body: dict, svc: LinhaCRUD = Depends(crud)):
    upd = svc.update(id, body)
    if not upd:
        raise HTTPException(404, "Linha não encontrada")
    return upd


@router.delete("/{id}", status_code=204, summary="Remover")
def remover(id: str, svc: LinhaCRUD = Depends(crud)):
    ok = svc.delete(id)
    if not ok:
        raise HTTPException(404, "Linha não encontrada")
    return
