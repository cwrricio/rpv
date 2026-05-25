from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from functions.repositories.discente_crud import DiscenteCRUD
from functions.domain.schemas import DiscenteCreate, DiscenteOut

router = APIRouter(tags=["Discentes"])


@lru_cache
def crud() -> DiscenteCRUD:
    return DiscenteCRUD()


@router.post("", status_code=201, response_model=DiscenteOut, summary="Criar")
@router.post("/", status_code=201, response_model=DiscenteOut, include_in_schema=False)
def criar(body: DiscenteCreate, svc: DiscenteCRUD = Depends(crud)):
    return svc.create(body.to_payload())


@router.get("", response_model=list[DiscenteOut], summary="Listar")
@router.get("/", response_model=list[DiscenteOut], include_in_schema=False)
def listar(svc: DiscenteCRUD = Depends(crud)):
    return svc.list()


@router.get("/{id}", response_model=DiscenteOut, summary="Obter")
def obter(id: str, svc: DiscenteCRUD = Depends(crud)):
    item = svc.get(id)
    if not item:
        raise HTTPException(404, "Discente não encontrado")
    return item


@router.patch("/{id}", response_model=DiscenteOut, summary="Atualizar")
def atualizar(id: str, body: DiscenteCreate, svc: DiscenteCRUD = Depends(crud)):
    upd = svc.update(id, body.to_payload())
    if not upd:
        raise HTTPException(404, "Discente não encontrado")
    return upd


@router.delete("/{id}", status_code=204, response_model=None, summary="Remover")
def remover(id: str, svc: DiscenteCRUD = Depends(crud)):
    ok = svc.delete(id)
    if not ok:
        raise HTTPException(404, "Discente não encontrado")
    return
