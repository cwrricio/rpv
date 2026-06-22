"""Testes de contrato do StoragePort — rodam contra todos os adaptadores.

Garante que FirebaseRTDBAdapter e PostgresAdapter se comportam identicamente
para as operações da StoragePort, incluindo o novo find_by_field (issue #6).
O adaptador Firebase usa o FakeDB em memória (sem credenciais reais);
o adaptador Postgres usa SQLite em memória (sem servidor).
"""
import uuid
import pytest

# ─── Adaptador Postgres (SQLite em memória) ───────────────────────────────────
pytest.importorskip("sqlalchemy")

from functions.adapters.postgres_adapter import PostgresAdapter

# ─── Adaptador Firebase fake ──────────────────────────────────────────────────
# Reutiliza o FakeDB definido em test_base_crud para evitar dependência real.
import sys
import types as _types


class _PushResult:
    def __init__(self, key: str):
        self.key = key


class FakeRef:
    def __init__(self, store: dict, parts: list):
        self._store = store
        self._parts = parts

    def _node(self, create: bool = False):
        cur = self._store
        for p in self._parts:
            if p not in cur:
                if create:
                    cur[p] = {}
                else:
                    return None
            cur = cur[p]
        return cur

    def child(self, key: str) -> "FakeRef":
        return FakeRef(self._store, self._parts + [str(key)])

    def push(self) -> _PushResult:
        return _PushResult(f"-F{uuid.uuid4().hex[:12]}")

    def get(self):
        node = self._node()
        return node if node is not None else None

    def set(self, value):
        parent = self._store
        for p in self._parts[:-1]:
            parent.setdefault(p, {})
            parent = parent[p]
        parent[self._parts[-1]] = value

    def update(self, patch: dict):
        node = self._node(create=True)
        if isinstance(node, dict):
            node.update(patch)

    def delete(self):
        parent = self._store
        for p in self._parts[:-1]:
            if p not in parent:
                return
            parent = parent[p]
        parent.pop(self._parts[-1], None)

    def order_by_child(self, field: str):
        return _ChildQuery(self, field)


class _ChildQuery:
    def __init__(self, ref: FakeRef, field: str):
        self._ref = ref
        self._field = field

    def equal_to(self, value):
        return _EqualToQuery(self._ref, self._field, value)


class _EqualToQuery:
    def __init__(self, ref: FakeRef, field: str, value):
        self._ref = ref
        self._field = field
        self._value = value

    def get(self):
        data = self._ref.get() or {}
        return {k: v for k, v in data.items() if isinstance(v, dict) and v.get(self._field) == self._value}


class FakeFirebaseAdapter:
    """FirebaseRTDBAdapter usando FakeRef em memória — sem credencial real."""

    def __init__(self):
        self._store: dict = {}

    def _ref(self, path_root: str) -> FakeRef:
        return FakeRef(self._store, [path_root])

    def create(self, path_root: str, obj: dict) -> dict:
        node = self._ref(path_root)
        key = node.push().key
        node.child(key).set(obj)
        return {"id": key, **obj}

    def upsert(self, path_root: str, id: str, obj: dict) -> dict:
        payload = {k: v for k, v in obj.items() if k != "id"}
        self._ref(path_root).child(id).set(payload)
        return {"id": id, **payload}

    def list(self, path_root: str) -> list:
        data = self._ref(path_root).get() or {}
        if isinstance(data, dict):
            return [{"id": k, **v} for k, v in data.items() if isinstance(v, dict)]
        return []

    def get(self, path_root: str, id: str):
        v = self._ref(path_root).child(id).get()
        if v is None:
            return None
        return {"id": id, **v} if isinstance(v, dict) else {"id": id, "value": v}

    def update(self, path_root: str, id: str, patch: dict):
        node = self._ref(path_root).child(id)
        if node.get() is None:
            return None
        node.update(patch)
        v = node.get() or {}
        return {"id": id, **v}

    def delete(self, path_root: str, id: str) -> bool:
        node = self._ref(path_root).child(id)
        if node.get() is None:
            return False
        node.delete()
        return True

    def find_by_field(self, path_root: str, field: str, value) -> list:
        snaps = self._ref(path_root).order_by_child(field).equal_to(value).get() or {}
        return [{"id": k, **v} for k, v in snaps.items() if isinstance(v, dict)]


# ─── Fixtures parametrizadas ──────────────────────────────────────────────────

def _make_pg():
    a = PostgresAdapter("sqlite+pysqlite:///:memory:")
    a.init_schema()
    return a


@pytest.fixture(params=["firebase_fake", "postgres_sqlite"])
def storage(request):
    if request.param == "firebase_fake":
        return FakeFirebaseAdapter()
    return _make_pg()


# ─── Contrato: operações básicas ──────────────────────────────────────────────

def test_create_atribui_id(storage):
    item = storage.create("col", {"x": 1})
    assert "id" in item
    assert item["x"] == 1


def test_create_e_get_paridade(storage):
    item = storage.create("col", {"nome": "Alice"})
    got = storage.get("col", item["id"])
    assert got == item


def test_upsert_preserva_id_e_substitui(storage):
    item = storage.upsert("col", "rtdb-id", {"nome": "Alice", "id": "ignorado"})
    assert item == {"id": "rtdb-id", "nome": "Alice"}
    assert storage.get("col", "rtdb-id") == item

    updated = storage.upsert("col", "rtdb-id", {"nome": "Alice 2"})
    assert updated == {"id": "rtdb-id", "nome": "Alice 2"}
    assert len(storage.list("col")) == 1


def test_list_vazio(storage):
    assert storage.list("col_vazia") == []


def test_list_retorna_todos(storage):
    storage.create("col", {"v": 1})
    storage.create("col", {"v": 2})
    assert len(storage.list("col")) == 2


def test_colecoes_isoladas(storage):
    storage.create("a", {"x": 1})
    storage.create("b", {"x": 2})
    assert len(storage.list("a")) == 1
    assert len(storage.list("b")) == 1


def test_get_inexistente_retorna_none(storage):
    assert storage.get("col", "nao-existe") is None


def test_update_merge_parcial(storage):
    item = storage.create("col", {"nome": "X", "tipo": "T"})
    updated = storage.update("col", item["id"], {"nome": "Y"})
    assert updated["nome"] == "Y"
    assert updated["tipo"] == "T"


def test_update_inexistente_retorna_none(storage):
    assert storage.update("col", "nao-existe", {"x": 1}) is None


def test_delete_existente(storage):
    item = storage.create("col", {"x": 1})
    assert storage.delete("col", item["id"]) is True
    assert storage.get("col", item["id"]) is None


def test_delete_inexistente_retorna_false(storage):
    assert storage.delete("col", "nao-existe") is False


def test_ciclo_completo(storage):
    a = storage.create("col", {"nome": "A"})
    b = storage.create("col", {"nome": "B"})
    assert len(storage.list("col")) == 2
    storage.update("col", a["id"], {"nome": "A2"})
    assert storage.get("col", a["id"])["nome"] == "A2"
    storage.delete("col", b["id"])
    assert len(storage.list("col")) == 1


# ─── Contrato: find_by_field (issue #6) ──────────────────────────────────────

def test_find_by_field_retorna_match(storage):
    storage.create("docentes", {"nome": "Alice", "orcid": "0000-0001-1111-0001"})
    storage.create("docentes", {"nome": "Bob",   "orcid": "0000-0001-1111-0002"})
    result = storage.find_by_field("docentes", "orcid", "0000-0001-1111-0001")
    assert len(result) == 1
    assert result[0]["nome"] == "Alice"


def test_find_by_field_sem_match_retorna_lista_vazia(storage):
    storage.create("docentes", {"nome": "Alice", "orcid": "0000-X"})
    assert storage.find_by_field("docentes", "orcid", "nao-existe") == []


def test_find_by_field_multiplos_matches(storage):
    storage.create("docentes", {"nome": "A", "tipo": "PERMANENTE"})
    storage.create("docentes", {"nome": "B", "tipo": "PERMANENTE"})
    storage.create("docentes", {"nome": "C", "tipo": "VISITANTE"})
    permanentes = storage.find_by_field("docentes", "tipo", "PERMANENTE")
    assert len(permanentes) == 2
