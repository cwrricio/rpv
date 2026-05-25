from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from functions.repositories.pesquisa_crud import PesquisaCRUD

router = APIRouter(tags=["Pesquisas"])  # sem prefix aqui; o prefix vem do main.py

_crud: Optional[PesquisaCRUD] = None
def crud() -> PesquisaCRUD:
    global _crud
    if _crud is None:
        _crud = PesquisaCRUD()
    return _crud

@router.post("", status_code=201, summary="Criar pesquisa")
@router.post("/", status_code=201, include_in_schema=False)
def criar(body: dict, svc: PesquisaCRUD = Depends(crud)):
    return svc.create(body)

@router.get("", summary="Listar pesquisas")
@router.get("/", include_in_schema=False)
def listar(svc: PesquisaCRUD = Depends(crud)):
    return svc.list()

@router.get("/{id}", summary="Obter pesquisa")
def obter(id: str, svc: PesquisaCRUD = Depends(crud)):
    item = svc.get(id)
    if not item:
        raise HTTPException(404, "Pesquisa não encontrada")
    return item

@router.patch("/{id}", summary="Atualizar pesquisa")
def atualizar(id: str, body: dict, svc: PesquisaCRUD = Depends(crud)):
    upd = svc.update(id, body)
    if not upd:
        raise HTTPException(404, "Pesquisa não encontrada")
    return upd

@router.delete("/{id}", status_code=204, summary="Remover pesquisa")
def remover(id: str, svc: PesquisaCRUD = Depends(crud)):
    ok = svc.delete(id)
    if not ok:
        raise HTTPException(404, "Pesquisa não encontrada")
    return
