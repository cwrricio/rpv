from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from functions.repositories.docente_crud import DocenteCRUD

router = APIRouter(tags=["Docentes"])

_crud: Optional[DocenteCRUD] = None
def crud() -> DocenteCRUD:
    global _crud
    if _crud is None:
        _crud = DocenteCRUD()
    return _crud

@router.post("", status_code=201, summary="Criar")
@router.post("/", status_code=201, include_in_schema=False)
def criar(body: dict, svc: DocenteCRUD = Depends(crud)):
    return svc.create(body)

@router.get("", summary="Listar")
@router.get("/", include_in_schema=False)
def listar(svc: DocenteCRUD = Depends(crud)):
    return svc.list()

@router.get("/{id}", summary="Obter")
def obter(id: str, svc: DocenteCRUD = Depends(crud)):
    item = svc.get(id)
    if not item:
        raise HTTPException(404, "Docente não encontrado")
    return item

@router.patch("/{id}", summary="Atualizar")
def atualizar(id: str, body: dict, svc: DocenteCRUD = Depends(crud)):
    upd = svc.update(id, body)
    if not upd:
        raise HTTPException(404, "Docente não encontrado")
    return upd

@router.delete("/{id}", status_code=204, summary="Remover")
def remover(id: str, svc: DocenteCRUD = Depends(crud)):
    ok = svc.delete(id)
    if not ok:
        raise HTTPException(404, "Docente não encontrado")
    return
