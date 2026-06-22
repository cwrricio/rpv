"""Testes da exportação versionada de dados (SSQM — Pessoa 3)."""
import csv
import json

from scripts.export_rtdb import _rows_from_node, write_node


def test_rows_from_node_dict_ignora_sentinela():
    data = {"_": True, "a1": {"nome": "A"}, "b2": {"nome": "B"}}
    rows = _rows_from_node(data)
    ids = sorted(r["id"] for r in rows)
    assert ids == ["a1", "b2"]
    assert all("nome" in r for r in rows)


def test_rows_from_node_valor_escalar():
    rows = _rows_from_node({"k": 42})
    assert rows == [{"id": "k", "value": 42}]


def test_write_node_gera_json_e_csv(tmp_path):
    data = {"a1": {"nome": "A", "tags": ["x", "y"]}, "b2": {"nome": "B"}}
    paths = write_node(str(tmp_path), "docentes", data)

    with open(paths["json"], encoding="utf-8") as f:
        assert json.load(f) == data

    with open(paths["csv"], encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert {r["id"] for r in rows} == {"a1", "b2"}
    # valores complexos viram JSON na coluna
    a = next(r for r in rows if r["id"] == "a1")
    assert json.loads(a["tags"]) == ["x", "y"]
