"""Testes de contrato para o adaptador SQL (SSQM — Pessoa 4 / TDD).

O PostgresAdapter implementa o mesmo StoragePort que o FirebaseRTDBAdapter, de
modo que trocar o backend não altera o comportamento dos repositórios. Para
rodar de forma portável e sem servidor, os testes usam SQLite via SQLAlchemy
(mesma engine, mesma camada de código). O comportamento contra PostgreSQL real
é exercitado pelo docker-compose.

Pular automaticamente se SQLAlchemy não estiver instalado.
"""
import pytest

pytest.importorskip("sqlalchemy")

from functions.adapters.postgres_adapter import PostgresAdapter  # noqa: E402


@pytest.fixture
def adapter():
    # SQLite em memória → cria as tabelas no schema genérico.
    a = PostgresAdapter("sqlite+pysqlite:///:memory:")
    a.init_schema()
    return a


def test_create_atribui_id_e_persiste(adapter):
    created = adapter.create("docentes", {"nome": "Maria", "tipo": "PERMANENTE"})
    assert "id" in created
    assert created["nome"] == "Maria"
    assert adapter.get("docentes", created["id"]) == created


def test_list_vazio_e_populado(adapter):
    assert adapter.list("docentes") == []
    adapter.create("docentes", {"nome": "A"})
    adapter.create("docentes", {"nome": "B"})
    nomes = sorted(item["nome"] for item in adapter.list("docentes"))
    assert nomes == ["A", "B"]


def test_colecoes_sao_isoladas(adapter):
    adapter.create("docentes", {"nome": "A"})
    adapter.create("discentes", {"nome": "B"})
    assert len(adapter.list("docentes")) == 1
    assert len(adapter.list("discentes")) == 1


def test_get_inexistente_retorna_none(adapter):
    assert adapter.get("docentes", "nao-existe") is None


def test_update_existente_faz_merge(adapter):
    created = adapter.create("docentes", {"nome": "Maria", "tipo": "PERMANENTE"})
    updated = adapter.update("docentes", created["id"], {"nome": "Maria Silva"})
    assert updated["nome"] == "Maria Silva"
    assert updated["tipo"] == "PERMANENTE"  # campo preservado (merge, não replace)
    assert adapter.get("docentes", created["id"])["nome"] == "Maria Silva"


def test_update_inexistente_retorna_none(adapter):
    assert adapter.update("docentes", "nao-existe", {"nome": "X"}) is None


def test_delete_existente_e_inexistente(adapter):
    created = adapter.create("docentes", {"nome": "Maria"})
    assert adapter.delete("docentes", created["id"]) is True
    assert adapter.get("docentes", created["id"]) is None
    assert adapter.delete("docentes", created["id"]) is False


def test_ciclo_completo(adapter):
    a = adapter.create("docentes", {"nome": "A"})
    b = adapter.create("docentes", {"nome": "B"})
    assert len(adapter.list("docentes")) == 2
    adapter.update("docentes", a["id"], {"nome": "A2"})
    assert adapter.get("docentes", a["id"])["nome"] == "A2"
    adapter.delete("docentes", b["id"])
    restantes = adapter.list("docentes")
    assert len(restantes) == 1
    assert restantes[0]["id"] == a["id"]
