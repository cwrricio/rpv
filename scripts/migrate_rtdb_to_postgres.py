#!/usr/bin/env python3
"""
Migrate RTDB JSON exports to PostgreSQL through the StoragePort.

Source format: files created by scripts/export_rtdb.py, usually:

    exports/<timestamp>/<node>.json

The script is conservative by default: without --apply it only validates and
prints a plan. When --apply is used, it preserves RTDB ids via StoragePort.upsert,
validates every migrated row, and writes a rollback manifest that can restore
the previous target state.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from functions.adapters.postgres_adapter import PostgresAdapter
from functions.repositories.ports import StoragePort
from scripts.export_rtdb import DEFAULT_NODES, _rows_from_node


RollbackEntry = Dict[str, Any]


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _payload(item: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in item.items() if k != "id"}


def _json_safe(value: Any) -> None:
    json.dumps(value, ensure_ascii=False)


def _source_files(source: Path, nodes: Optional[Iterable[str]]) -> tuple[list[tuple[str, Path]], list[str]]:
    if source.is_file():
        return [(source.stem, source)], []

    if not source.is_dir():
        raise FileNotFoundError(f"Fonte nao encontrada: {source}")

    wanted = list(nodes or DEFAULT_NODES)
    found: list[tuple[str, Path]] = []
    missing: list[str] = []

    for node in wanted:
        path = source / f"{node}.json"
        if path.exists():
            found.append((node, path))
        else:
            missing.append(node)

    if not found and nodes is None:
        found = [(path.stem, path) for path in sorted(source.glob("*.json"))]
        missing = []

    if not found:
        raise FileNotFoundError(
            f"Nenhum JSON de exportacao encontrado em {source}. "
            "Informe --nodes para export parcial ou confira o caminho."
        )

    return found, missing


def load_export(source: str | Path, nodes: Optional[Iterable[str]] = None) -> dict[str, dict[str, Dict[str, Any]]]:
    """Load RTDB export JSON files as {collection: {id: payload}}."""
    source_path = Path(source)
    files, _ = _source_files(source_path, nodes)
    collections: dict[str, dict[str, Dict[str, Any]]] = {}

    for collection, path in files:
        with path.open(encoding="utf-8") as handle:
            raw = json.load(handle)

        rows: dict[str, Dict[str, Any]] = {}
        for row in _rows_from_node(raw):
            row_id = str(row.get("id", "")).strip()
            if not row_id:
                raise ValueError(f"{path}: item sem id valido")
            if row_id in rows:
                raise ValueError(f"{path}: id duplicado na colecao {collection}: {row_id}")

            payload = _payload(row)
            _json_safe(payload)
            rows[row_id] = payload

        collections[collection] = rows

    return collections


def _target_state(storage: StoragePort, collection: str, item_id: str) -> Optional[Dict[str, Any]]:
    item = storage.get(collection, item_id)
    return _payload(item) if item else None


def _validate_target(
    storage: StoragePort,
    expected: dict[str, dict[str, Dict[str, Any]]],
    *,
    replace: bool,
) -> list[str]:
    errors: list[str] = []

    for collection, rows in expected.items():
        for item_id, payload in rows.items():
            actual = _target_state(storage, collection, item_id)
            if actual != payload:
                errors.append(f"{collection}/{item_id}: payload divergente apos migracao")

        if replace:
            expected_ids = set(rows)
            actual_ids = {item["id"] for item in storage.list(collection) if isinstance(item, dict)}
            extra = actual_ids - expected_ids
            missing = expected_ids - actual_ids
            if extra:
                errors.append(f"{collection}: ids extras apos --replace: {sorted(extra)}")
            if missing:
                errors.append(f"{collection}: ids ausentes apos --replace: {sorted(missing)}")

    return errors


def _rollback_entries(storage: StoragePort, entries: list[RollbackEntry]) -> None:
    for entry in reversed(entries):
        collection = entry["collection"]
        item_id = entry["id"]
        previous = entry["previous"]
        if previous is None:
            storage.delete(collection, item_id)
        else:
            storage.upsert(collection, item_id, previous)


def _default_manifest_path(source: Path) -> Path:
    base_dir = source if source.is_dir() else source.parent
    return base_dir / f"migration_rollback_{_utc_stamp()}.json"


def _write_manifest(
    path: Path,
    *,
    source: Path,
    replace: bool,
    entries: list[RollbackEntry],
) -> Path:
    manifest = {
        "version": 1,
        "created_at": _utc_stamp(),
        "source": str(source),
        "replace": replace,
        "entries": entries,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    return path


def migrate_export(
    source: str | Path,
    storage: StoragePort,
    *,
    nodes: Optional[Iterable[str]] = None,
    apply: bool = False,
    replace: bool = False,
    manifest_out: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Validate and optionally migrate an RTDB JSON export into the target storage."""
    source_path = Path(source)
    files, missing_nodes = _source_files(source_path, nodes)
    collections = load_export(source_path, [collection for collection, _ in files])
    total_rows = sum(len(rows) for rows in collections.values())

    report: dict[str, Any] = {
        "source": str(source_path),
        "apply": apply,
        "replace": replace,
        "collections": [
            {"collection": collection, "rows": len(rows)}
            for collection, rows in collections.items()
        ],
        "missing_nodes": missing_nodes,
        "total_rows": total_rows,
        "rollback_manifest": None,
    }

    if not apply:
        return report

    rollback_entries: list[RollbackEntry] = []

    try:
        for collection, rows in collections.items():
            source_ids = set(rows)

            if replace:
                for item in storage.list(collection):
                    item_id = item.get("id") if isinstance(item, dict) else None
                    if item_id and item_id not in source_ids:
                        previous = _payload(item)
                        rollback_entries.append(
                            {
                                "collection": collection,
                                "id": item_id,
                                "previous": previous,
                                "migrated": None,
                            }
                        )
                        storage.delete(collection, item_id)

            for item_id, payload in rows.items():
                previous = _target_state(storage, collection, item_id)
                rollback_entries.append(
                    {
                        "collection": collection,
                        "id": item_id,
                        "previous": previous,
                        "migrated": payload,
                    }
                )
                storage.upsert(collection, item_id, payload)

        errors = _validate_target(storage, collections, replace=replace)
        if errors:
            raise RuntimeError("Validacao falhou: " + "; ".join(errors))

    except Exception:
        _rollback_entries(storage, rollback_entries)
        raise

    manifest_path = Path(manifest_out) if manifest_out else _default_manifest_path(source_path)
    report["rollback_manifest"] = str(
        _write_manifest(
            manifest_path,
            source=source_path,
            replace=replace,
            entries=rollback_entries,
        )
    )
    return report


def rollback_from_manifest(storage: StoragePort, manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path)
    with path.open(encoding="utf-8") as handle:
        manifest = json.load(handle)

    entries = manifest.get("entries")
    if not isinstance(entries, list):
        raise ValueError(f"Manifesto invalido: {path}")

    _rollback_entries(storage, entries)
    return {"rolled_back_entries": len(entries), "manifest": str(path)}


def _postgres_storage(database_url: Optional[str]) -> PostgresAdapter:
    adapter = PostgresAdapter(database_url)
    adapter.init_schema()
    return adapter


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migra export JSON do Firebase RTDB para PostgreSQL."
    )
    parser.add_argument("--source", help="Arquivo JSON ou diretorio exports/<timestamp>.")
    parser.add_argument("--nodes", nargs="*", help="Colecoes/nos a migrar.")
    parser.add_argument("--database-url", help="SQLAlchemy DATABASE_URL do PostgreSQL.")
    parser.add_argument("--apply", action="store_true", help="Executa a migracao. Sem isso e dry-run.")
    parser.add_argument("--replace", action="store_true", help="Remove ids extras nas colecoes migradas.")
    parser.add_argument("--manifest-out", help="Caminho do manifesto de rollback.")
    parser.add_argument("--rollback", help="Reverte uma migracao usando o manifesto gerado.")
    args = parser.parse_args()

    storage = _postgres_storage(args.database_url)

    if args.rollback:
        report = rollback_from_manifest(storage, args.rollback)
    else:
        if not args.source:
            parser.error("--source e obrigatorio exceto com --rollback")
        report = migrate_export(
            args.source,
            storage,
            nodes=args.nodes,
            apply=args.apply,
            replace=args.replace,
            manifest_out=args.manifest_out,
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
