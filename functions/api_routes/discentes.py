from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from functions.crud.discente_crud import DiscenteCRUD

router = APIRouter(tags=["Discentes"])

_crud: Optional[DiscenteCRUD] = None
def crud() -> DiscenteCRUD:
    global _crud
    if _crud is None:
        _crud = DiscenteCRUD()
    return _crud

@router.post("", status_code=201, summary="Criar")
@router.post("/", status_code=201, include_in_schema=False)
def criar(body: dict, svc: DiscenteCRUD = Depends(crud)):
    return svc.create(body)

@router.get("", summary="Listar")
@router.get("/", include_in_schema=False)
def listar(svc: DiscenteCRUD = Depends(crud)):
    return svc.list()

@router.get("/{id}", summary="Obter")
def obter(id: str, svc: DiscenteCRUD = Depends(crud)):
    item = svc.get(id)
    if not item:
        raise HTTPException(404, "Discente não encontrado")
    return item

@router.patch("/{id}", summary="Atualizar")
def atualizar(id: str, body: dict, svc: DiscenteCRUD = Depends(crud)):
    upd = svc.update(id, body)
    if not upd:
        raise HTTPException(404, "Discente não encontrado")
    return upd

@router.delete("/{id}", status_code=204, summary="Remover")
def remover(id: str, svc: DiscenteCRUD = Depends(crud)):
    ok = svc.delete(id)
    if not ok:
        raise HTTPException(404, "Discente não encontrado")
    return
