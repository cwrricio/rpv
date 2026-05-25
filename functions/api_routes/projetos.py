from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException

from functions.repositories.projeto_crud import ProjetoCRUD
from functions.domain.schemas import ProjetoCreate, ProjetoOut

router = APIRouter(tags=["Projetos"])


@lru_cache
def crud() -> ProjetoCRUD:
    return ProjetoCRUD()


@router.post("", status_code=201, response_model=ProjetoOut, summary="Criar")
@router.post("/", status_code=201, response_model=ProjetoOut, include_in_schema=False)
def criar(body: ProjetoCreate, svc: ProjetoCRUD = Depends(crud)):
    return svc.create(body.to_payload())


@router.get("", response_model=list[ProjetoOut], summary="Listar")
@router.get("/", response_model=list[ProjetoOut], include_in_schema=False)
def listar(svc: ProjetoCRUD = Depends(crud)):
    return svc.list()


@router.get("/{id}", response_model=ProjetoOut, summary="Obter")
def obter(id: str, svc: ProjetoCRUD = Depends(crud)):
    item = svc.get(id)
    if not item:
        raise HTTPException(404, "Projeto não encontrado")
    return item


@router.patch("/{id}", response_model=ProjetoOut, summary="Atualizar")
def atualizar(id: str, body: ProjetoCreate, svc: ProjetoCRUD = Depends(crud)):
    upd = svc.update(id, body.to_payload())
    if not upd:
        raise HTTPException(404, "Projeto não encontrado")
    return upd


@router.delete("/{id}", status_code=204, response_model=None, summary="Remover")
def remover(id: str, svc: ProjetoCRUD = Depends(crud)):
    ok = svc.delete(id)
    if not ok:
        raise HTTPException(404, "Projeto não encontrado")
    return
