"""Testes de rota para api_routes/docentes.py (Frente 4.4).

Usam o TestClient do FastAPI com um CRUD fake em memória injetado via
dependency_overrides — assim validam a validação Pydantic, os status codes e a
serialização response_model sem tocar o Firebase nem importar main.py
(que inicializa o Firebase no import).

Inclui ainda um teste direto de DocenteCRUD.find_by_orcid garantindo que ele
usa self.ref() e não lança AttributeError (o antigo self._node()).
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from functions.api_routes.docentes import crud, router
from functions.crud.docente_crud import DocenteCRUD


# --------------------------------------------------------------------------- #
# CRUD fake em memória
# --------------------------------------------------------------------------- #
class FakeDocenteCRUD:
    def __init__(self):
        self.store: dict[str, dict] = {}
        self._seq = 0

    def create(self, data: dict) -> dict:
        self._seq += 1
        key = f"id{self._seq}"
        self.store[key] = dict(data)
        return {"id": key, **self.store[key]}

    def list(self) -> list[dict]:
        return [{"id": k, **v} for k, v in self.store.items()]

    def get(self, id: str):
        v = self.store.get(id)
        return {"id": id, **v} if v is not None else None

    def update(self, id: str, patch: dict):
        if id not in self.store:
            return None
        self.store[id].update(patch)
        return {"id": id, **self.store[id]}

    def delete(self, id: str) -> bool:
        return self.store.pop(id, None) is not None


@pytest.fixture
def fake():
    return FakeDocenteCRUD()


@pytest.fixture
def client(fake):
    app = FastAPI()
    app.include_router(router, prefix="/docentes")
    app.dependency_overrides[crud] = lambda: fake
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --------------------------------------------------------------------------- #
# Criação + validação Pydantic
# --------------------------------------------------------------------------- #
def test_criar_docente_valido_retorna_201(client):
    resp = client.post("/docentes", json={"nome": "Maria", "tipo": "PERMANENTE"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"].startswith("id")
    assert body["nome"] == "Maria"
    assert body["tipo"] == "PERMANENTE"


def test_criar_docente_normaliza_tipo_minusculo(client):
    resp = client.post("/docentes", json={"nome": "Ana", "tipo": "colaborador"})
    assert resp.status_code == 201
    assert resp.json()["tipo"] == "COLABORADOR"


def test_criar_docente_tipo_invalido_retorna_422(client):
    resp = client.post("/docentes", json={"nome": "Maria", "tipo": "INVALIDO"})
    assert resp.status_code == 422


# --------------------------------------------------------------------------- #
# Listagem / obtenção
# --------------------------------------------------------------------------- #
def test_listar_vazio(client):
    resp = client.get("/docentes")
    assert resp.status_code == 200
    assert resp.json() == []


def test_criar_e_obter(client):
    created = client.post("/docentes", json={"nome": "Maria", "tipo": "PERMANENTE"}).json()
    resp = client.get(f"/docentes/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Maria"


def test_obter_inexistente_retorna_404(client):
    resp = client.get("/docentes/nao-existe")
    assert resp.status_code == 404


# --------------------------------------------------------------------------- #
# Atualização / remoção
# --------------------------------------------------------------------------- #
def test_atualizar_existente(client):
    created = client.post("/docentes", json={"nome": "Maria", "tipo": "PERMANENTE"}).json()
    resp = client.patch(f"/docentes/{created['id']}", json={"nome": "Maria Silva"})
    assert resp.status_code == 200
    assert resp.json()["nome"] == "Maria Silva"


def test_atualizar_inexistente_retorna_404(client):
    resp = client.patch("/docentes/nao-existe", json={"nome": "X"})
    assert resp.status_code == 404


def test_remover_existente_e_depois_404(client):
    created = client.post("/docentes", json={"nome": "Maria", "tipo": "PERMANENTE"}).json()
    assert client.delete(f"/docentes/{created['id']}").status_code == 204
    assert client.delete(f"/docentes/{created['id']}").status_code == 404


# --------------------------------------------------------------------------- #
# find_by_orcid — bug histórico self._node() -> self.ref()
# --------------------------------------------------------------------------- #
def test_find_by_orcid_usa_ref_e_nao_lanca_attributeerror():
    svc = DocenteCRUD()  # __init__ só define path_root; não toca o Firebase

    fake_ref = MagicMock()
    fake_ref.order_by_child.return_value.equal_to.return_value.get.return_value = {
        "id1": {"nome": "Maria", "orcid": "0000-0001-0000-0001"},
    }
    svc.ref = lambda: fake_ref  # substitui o acesso ao banco

    resultado = svc.find_by_orcid("0000-0001-0000-0001")

    assert resultado == [{"id": "id1", "nome": "Maria", "orcid": "0000-0001-0000-0001"}]
    fake_ref.order_by_child.assert_called_once_with("orcid")


def test_docente_crud_create_rejeita_tipo_invalido():
    svc = DocenteCRUD()
    with pytest.raises(ValueError):
        svc.create({"nome": "Maria", "tipo": "INVALIDO"})  # falha antes de tocar o banco
