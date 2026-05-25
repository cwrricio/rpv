from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

RankingItem = dict[str, int | str]


def build_author_product_ranking(
    produtos_provider: Callable[[], Sequence[Mapping[str, Any]]],
) -> list[RankingItem]:
    linked_ranking = _ranking_from_linked_docentes()
    if linked_ranking:
        return linked_ranking

    produtos = produtos_provider() or []
    return _ranking_from_produtos(produtos)


def _ranking_from_linked_docentes() -> list[RankingItem]:
    try:
        from functions.common.dbref import ref

        autores_node = ref("autores").get() or {}
        counts_by_docente: dict[str, int] = {}

        for value in autores_node.values():
            if not isinstance(value, dict):
                continue
            docente_id = value.get("docente_id") or value.get("docenteId")
            if docente_id:
                docente_key = str(docente_id)
                counts_by_docente[docente_key] = counts_by_docente.get(docente_key, 0) + 1

        if not counts_by_docente:
            return []

        docentes_node = ref("docentes").get() or {}
        ranking: list[RankingItem] = []

        for docente_id, count in counts_by_docente.items():
            docente = docentes_node.get(docente_id) if isinstance(docentes_node, dict) else None
            name = None
            if isinstance(docente, dict):
                name = docente.get("nome") or docente.get("name") or docente.get("display_name")
            ranking.append({"name": str(name or docente_id), "count": count})

        ranking.sort(key=lambda item: -int(item["count"]))
        return ranking
    except Exception:
        return []


def _ranking_from_produtos(produtos: Sequence[Mapping[str, Any]]) -> list[RankingItem]:
    counts: dict[str, int] = {}

    for produto in produtos:
        autores_field = (
            produto.get("autores")
            or produto.get("authorships")
            or produto.get("autores_list")
            or produto.get("authors")
        )
        if not autores_field:
            continue

        if isinstance(autores_field, list):
            for autor in autores_field:
                name = _author_name(autor)
                if name:
                    counts[name] = counts.get(name, 0) + 1
        elif isinstance(autores_field, str):
            for name in [part.strip() for part in autores_field.split(",") if part.strip()]:
                counts[name] = counts.get(name, 0) + 1

    ranking = [{"name": name, "count": count} for name, count in counts.items()]
    ranking.sort(key=lambda item: -int(item["count"]))
    return ranking


def _author_name(autor: Any) -> str | None:
    if isinstance(autor, str):
        name = autor
    elif isinstance(autor, dict):
        author = autor.get("author")
        name = autor.get("name") or autor.get("author_name")
        if not name and isinstance(author, dict):
            name = author.get("display_name")
    else:
        name = None

    if not name:
        return None

    normalized = str(name).strip()
    return normalized or None
