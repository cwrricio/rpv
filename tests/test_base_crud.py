"""Testes de integração para repositories/BaseCRUD (Frente 4.6).

Há duas camadas:

1. Um RTDB **fake em memória** (FakeDB/FakeRef) que implementa o subconjunto da
   API do firebase_admin.db usado por BaseCRUD (push/child/set/get/update/
   delete). Exercita o ciclo completo create/list/get/update/delete sempre,
   sem dependência externa — é o teste que valida a lógica do repositório.

2. Um teste com **emulador Firebase real**, executado apenas quando a variável
   FIREBASE_DATABASE_EMULATOR_HOST está definida (ex.:
   ``firebase emulators:start --only database``). Pulado caso contrário.

Observação: nesta branch a pasta ainda se chama functions/crud/ (a renomeação
para repositories/ é da Frente 2). BaseCRUD é o mesmo componente.
"""

import os
import uuid

import pytest

import functions.crud.base as base_module
from functions.crud.base import BaseCRUD


# --------------------------------------------------------------------------- #
# RTDB fake em memória
# --------------------------------------------------------------------------- #
class _PushResult:
    def __init__(self, key: str):
        self.key = key


class FakeRef:
    """Referência sobre um dict aninhado, imitando firebase_admin.db.Reference."""

    def __init__(self, db: "FakeDB", parts: list[str]):
        self._db = db
        self._parts = parts

    def child(self, key: str) -> "FakeRef":
        return FakeRef(self._db, self._parts + [str(key)])

    def push(self) -> _PushResult:
        return _PushResult(f"-Fake{uuid.uuid4().hex[:12]}")

    def get(self):
        cur = self._db.data
        for p in self._parts:
            if not isinstance(cur, dict) or p not in cur:
                return None
            cur = cur[p]
        return cur

    def set(self, value):
        cur = self._db.data
        for p in self._parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[self._parts[-1]] = value

    def update(self, patch: dict):
        cur = self._db.data
        for p in self._parts:
            cur = cur.setdefault(p, {})
        cur.update(patch)

    def delete(self):
        cur = self._db.data
        for p in self._parts[:-1]:
            if not isinstance(cur, dict) or p not in cur:
                return
            cur = cur[p]
        if isinstance(cur, dict):
            cur.pop(self._parts[-1], None)


class FakeDB:
    def __init__(self):
        self.data: dict = {}

    def reference(self, path: str) -> FakeRef:
        parts = [p for p in path.strip("/").split("/") if p] if path else []
        return FakeRef(self, parts)


@pytest.fixture
def crud(monkeypatch):
    """BaseCRUD apontando para um RTDB fake isolado por teste."""
    fake_db = FakeDB()
    monkeypatch.setattr(base_module, "_db", lambda: fake_db)
    return BaseCRUD("docentes")


# --------------------------------------------------------------------------- #
# Ciclo CRUD completo com o fake
# --------------------------------------------------------------------------- #
def test_create_atribui_id_e_persiste(crud):
    created = crud.create({"nome": "Maria", "tipo": "PERMANENTE"})
    assert "id" in created
    assert created["nome"] == "Maria"
    assert crud.get(created["id"]) == created


def test_list_vazio_e_populado(crud):
    assert crud.list() == []
    crud.create({"nome": "A"})
    crud.create({"nome": "B"})
    nomes = sorted(item["nome"] for item in crud.list())
    assert nomes == ["A", "B"]


def test_get_inexistente_retorna_none(crud):
    assert crud.get("nao-existe") is None


def test_update_existente(crud):
    created = crud.create({"nome": "Maria", "tipo": "PERMANENTE"})
    updated = crud.update(created["id"], {"nome": "Maria Silva"})
    assert updated["nome"] == "Maria Silva"
    assert updated["tipo"] == "PERMANENTE"  # campo preservado
    assert crud.get(created["id"])["nome"] == "Maria Silva"


def test_update_inexistente_retorna_none(crud):
    assert crud.update("nao-existe", {"nome": "X"}) is None


def test_delete_existente_e_inexistente(crud):
    created = crud.create({"nome": "Maria"})
    assert crud.delete(created["id"]) is True
    assert crud.get(created["id"]) is None
    assert crud.delete(created["id"]) is False


def test_ciclo_completo(crud):
    a = crud.create({"nome": "A"})
    b = crud.create({"nome": "B"})
    assert len(crud.list()) == 2
    crud.update(a["id"], {"nome": "A2"})
    assert crud.get(a["id"])["nome"] == "A2"
    crud.delete(b["id"])
    restantes = crud.list()
    assert len(restantes) == 1
    assert restantes[0]["id"] == a["id"]


# --------------------------------------------------------------------------- #
# Integração com emulador Firebase real (opt-in)
# --------------------------------------------------------------------------- #
emulator_required = pytest.mark.skipif(
    not os.getenv("FIREBASE_DATABASE_EMULATOR_HOST"),
    reason="defina FIREBASE_DATABASE_EMULATOR_HOST e rode "
    "`firebase emulators:start --only database` para executar",
)


@emulator_required
def test_base_crud_contra_emulador():
    import firebase_admin
    from firebase_admin import credentials, db

    app_name = f"test-{uuid.uuid4().hex[:8]}"
    project_id = os.getenv("PROJECT_ID", "test-project")
    database_url = os.getenv(
        "RTDB_URL", f"https://{project_id}-default-rtdb.firebaseio.com"
    )
    try:
        cred = credentials.ApplicationDefault()
    except Exception:  # noqa: BLE001 — emulador não exige credencial real
        from unittest.mock import MagicMock

        cred = MagicMock(spec=credentials.Base)

    app = firebase_admin.initialize_app(
        cred, {"projectId": project_id, "databaseURL": database_url}, name=app_name
    )
    try:
        path_root = f"test_docentes_{uuid.uuid4().hex[:8]}"

        class _EmuCRUD(BaseCRUD):
            def ref(self):
                return db.reference(path_root, app=app)

        crud = _EmuCRUD(path_root)

        created = crud.create({"nome": "Maria", "tipo": "PERMANENTE"})
        assert crud.get(created["id"])["nome"] == "Maria"

        crud.update(created["id"], {"nome": "Maria Silva"})
        assert crud.get(created["id"])["nome"] == "Maria Silva"

        assert any(i["id"] == created["id"] for i in crud.list())

        assert crud.delete(created["id"]) is True
        assert crud.get(created["id"]) is None
    finally:
        db.reference(path_root, app=app).delete()
        firebase_admin.delete_app(app)
