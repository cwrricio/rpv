import json

import pytest

pytest.importorskip("sqlalchemy")

from functions.adapters.postgres_adapter import PostgresAdapter
from scripts.migrate_rtdb_to_postgres import (
    load_export,
    migrate_export,
    rollback_from_manifest,
)


@pytest.fixture
def storage():
    adapter = PostgresAdapter("sqlite+pysqlite:///:memory:")
    adapter.init_schema()
    return adapter


def _write_export(tmp_path, node, data):
    path = tmp_path / f"{node}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_export_normaliza_no_rtdb(tmp_path):
    _write_export(
        tmp_path,
        "docentes",
        {"_": True, "d1": {"nome": "Maria"}, "d2": 42},
    )

    data = load_export(tmp_path, nodes=["docentes"])

    assert data == {
        "docentes": {
            "d1": {"nome": "Maria"},
            "d2": {"value": 42},
        }
    }


def test_migrate_export_dry_run_nao_escreve(storage, tmp_path):
    _write_export(tmp_path, "docentes", {"d1": {"nome": "Maria"}})

    report = migrate_export(tmp_path, storage, nodes=["docentes"])

    assert report["apply"] is False
    assert report["total_rows"] == 1
    assert storage.list("docentes") == []


def test_migrate_export_preserva_ids_e_gera_manifesto(storage, tmp_path):
    _write_export(tmp_path, "docentes", {"d1": {"nome": "Maria"}})
    manifest = tmp_path / "rollback.json"

    report = migrate_export(
        tmp_path,
        storage,
        nodes=["docentes"],
        apply=True,
        manifest_out=manifest,
    )

    assert report["rollback_manifest"] == str(manifest)
    assert storage.get("docentes", "d1") == {"id": "d1", "nome": "Maria"}
    assert manifest.exists()


def test_rollback_from_manifest_restaura_estado_anterior(storage, tmp_path):
    storage.upsert("docentes", "d1", {"nome": "Antes"})
    _write_export(tmp_path, "docentes", {"d1": {"nome": "Depois"}, "d2": {"nome": "Novo"}})
    manifest = tmp_path / "rollback.json"

    migrate_export(
        tmp_path,
        storage,
        nodes=["docentes"],
        apply=True,
        manifest_out=manifest,
    )
    assert storage.get("docentes", "d1")["nome"] == "Depois"
    assert storage.get("docentes", "d2")["nome"] == "Novo"

    report = rollback_from_manifest(storage, manifest)

    assert report["rolled_back_entries"] == 2
    assert storage.get("docentes", "d1") == {"id": "d1", "nome": "Antes"}
    assert storage.get("docentes", "d2") is None


def test_migrate_export_replace_remove_extras_e_rollback_restaura(storage, tmp_path):
    storage.upsert("docentes", "extra", {"nome": "Extra"})
    _write_export(tmp_path, "docentes", {"d1": {"nome": "Maria"}})
    manifest = tmp_path / "rollback.json"

    migrate_export(
        tmp_path,
        storage,
        nodes=["docentes"],
        apply=True,
        replace=True,
        manifest_out=manifest,
    )

    assert storage.get("docentes", "extra") is None
    assert storage.get("docentes", "d1") == {"id": "d1", "nome": "Maria"}

    rollback_from_manifest(storage, manifest)

    assert storage.get("docentes", "extra") == {"id": "extra", "nome": "Extra"}
    assert storage.get("docentes", "d1") is None
