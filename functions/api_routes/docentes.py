from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from functions.crud.docente_crud import DocenteCRUD
from functions.domain.schemas import DocenteCreate, DocenteOut

router = APIRouter(tags=["Docentes"])


@lru_cache
def crud() -> DocenteCRUD:
    return DocenteCRUD()


@router.post("", status_code=201, response_model=DocenteOut, summary="Criar")
@router.post("/", status_code=201, response_model=DocenteOut, include_in_schema=False)
def criar(body: DocenteCreate, svc: DocenteCRUD = Depends(crud)):
    return svc.create(body.to_payload())


@router.get("", response_model=list[DocenteOut], summary="Listar")
@router.get("/", response_model=list[DocenteOut], include_in_schema=False)
def listar(svc: DocenteCRUD = Depends(crud)):
    return svc.list()


@router.get("/{id}", response_model=DocenteOut, summary="Obter")
def obter(id: str, svc: DocenteCRUD = Depends(crud)):
    item = svc.get(id)
    if not item:
        raise HTTPException(404, "Docente não encontrado")
    return item


@router.patch("/{id}", response_model=DocenteOut, summary="Atualizar")
def atualizar(id: str, body: DocenteCreate, svc: DocenteCRUD = Depends(crud)):
    upd = svc.update(id, body.to_payload())
    if not upd:
        raise HTTPException(404, "Docente não encontrado")
    return upd


@router.delete("/{id}", status_code=204, response_model=None, summary="Remover")
def remover(id: str, svc: DocenteCRUD = Depends(crud)):
    ok = svc.delete(id)
    if not ok:
        raise HTTPException(404, "Docente não encontrado")
    return
