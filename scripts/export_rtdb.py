#!/usr/bin/env python3
"""
Exportação versionada dos dados (SSQM — saída de emergência / soberania de dados).

Lê os nós principais do RTDB através de functions/common/dbref.ref (único ponto
de contato com o Firebase) e grava cada nó como JSON e CSV em
`exports/<timestamp>/`. Serve como backup portável e como base para a migração
RTDB -> PostgreSQL.

Uso:
    python scripts/export_rtdb.py
    python scripts/export_rtdb.py --nodes autores produtos --out exports
"""
import argparse
import csv
import json
import os
from datetime import datetime
from typing import Dict, Any, Iterable, List

# Nós canônicos do sistema (ver docs/DATA_MODEL.md).
DEFAULT_NODES = [
    "autores",
    "autores_flat",
    "produtos",
    "veiculos",
    "docentes",
    "discentes",
    "linhas",
    "projetos",
    "pesquisas",
]


def _rows_from_node(data: Any) -> List[Dict[str, Any]]:
    """Normaliza um nó RTDB (dict de id->obj) para lista de linhas com id."""
    if isinstance(data, dict):
        rows = []
        for k, v in data.items():
            if k == "_":
                continue
            if isinstance(v, dict):
                rows.append({"id": k, **v})
            else:
                rows.append({"id": k, "value": v})
        return rows
    if isinstance(data, list):
        return [{"id": str(i), **(v if isinstance(v, dict) else {"value": v})}
                for i, v in enumerate(data)]
    return []


def write_node(out_dir: str, node: str, data: Any) -> Dict[str, str]:
    """Grava um nó em JSON e CSV. Retorna os caminhos gerados."""
    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, f"{node}.json")
    csv_path = os.path.join(out_dir, f"{node}.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    rows = _rows_from_node(data)
    # Campos = união de todas as chaves de primeiro nível (valores complexos viram JSON).
    fields: List[str] = []
    for r in rows:
        for k in r.keys():
            if k not in fields:
                fields.append(k)
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({
                k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                for k, v in r.items()
            })
    return {"json": json_path, "csv": csv_path}


def export(nodes: Iterable[str], out_root: str) -> str:
    """Exporta os nós informados; retorna o diretório com timestamp criado."""
    from functions.common.dbref import ref  # import tardio: só quando realmente exporta

    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.join(out_root, stamp)
    for node in nodes:
        data = ref(node).get() or {}
        paths = write_node(out_dir, node, data)
        print(f"[ok] {node}: {paths['json']} / {paths['csv']}")
    print(f"\nExport completo em: {out_dir}")
    return out_dir


def main():
    parser = argparse.ArgumentParser(description="Exporta nós do RTDB para JSON/CSV.")
    parser.add_argument("--nodes", nargs="*", default=DEFAULT_NODES,
                        help="Nós a exportar (default: todos os canônicos).")
    parser.add_argument("--out", default="exports", help="Diretório raiz de saída.")
    args = parser.parse_args()
    export(args.nodes, args.out)


if __name__ == "__main__":
    main()
