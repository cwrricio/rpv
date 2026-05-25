"""Camada de Aplicação: métricas bibliométricas de autores.

Toda a lógica de agregação que antes vivia no handler de rota
``GET /autores/{id}/metrics`` (``main.py``) foi movida para cá. As funções são
**puras**: recebem o nó ``autores_flat/{id}`` (um ``dict`` já lido do banco) e
não acessam o Firebase. Isso as torna testáveis sem emulador nem rede
(ver ``tests/test_analytics.py``).

Índices implementados:
- ``h_index``  — maior h tal que h publicações têm ≥ h citações cada.
- ``i10_index`` — número de publicações com ≥ 10 citações (limiar configurável).
- ``h5_index`` — h-index restrito às publicações dos últimos ``H5_WINDOW_YEARS``
  anos. O ano de referência é, por padrão, o ano da publicação mais recente do
  próprio autor (determinístico — não depende do relógio), mas pode ser passado
  explicitamente via ``reference_year`` para facilitar testes.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

SAMPLE_SIZE = 10
TOP_N = 10
H5_WINDOW_YEARS = 5
I10_THRESHOLD = 10


def extract_works(node: Mapping[str, Any] | None) -> list[dict]:
    """Normaliza ``autores_flat/{id}.works`` (map ou lista) em lista de obras.

    Aceita as variações de chave usadas pelos dados crus (``works``/``work``) e
    ignora a sentinela ``"_"`` e valores que não sejam ``dict``.
    """
    if not node:
        return []
    works = node.get("works") or node.get("work") or {}
    if isinstance(works, dict):
        return [{**v, "id": k} for k, v in works.items() if k != "_" and isinstance(v, dict)]
    if isinstance(works, list):
        return [w for w in works if isinstance(w, dict)]
    return []


def _citation_count(work: Mapping[str, Any]) -> int:
    """Citações de uma obra, tolerando as várias chaves e tipos dos dados crus."""
    cited = work.get("cited_by_count") or work.get("citations") or work.get("cited_by") or 0
    try:
        return int(cited)
    except (TypeError, ValueError):
        return 0


def _publication_year(work: Mapping[str, Any]) -> int | None:
    """Ano de publicação de uma obra, ou ``None`` se ausente/inválido."""
    year = work.get("year") or work.get("ano") or work.get("published_year")
    if year is None:
        return None
    try:
        return int(year)
    except (TypeError, ValueError):
        return None


def compute_h_index(citations: Sequence[int]) -> int:
    """h-index: maior h tal que há h itens com pelo menos h citações."""
    h = 0
    for i, c in enumerate(sorted(citations, reverse=True), start=1):
        if c >= i:
            h = i
        else:
            break
    return h


def compute_i10_index(citations: Sequence[int], threshold: int = I10_THRESHOLD) -> int:
    """i10-index: quantidade de publicações com ao menos ``threshold`` citações."""
    return sum(1 for c in citations if c >= threshold)


def compute_h5_index(
    works: Sequence[Mapping[str, Any]],
    reference_year: int | None = None,
    window: int = H5_WINDOW_YEARS,
) -> int:
    """h-index considerando apenas obras dos últimos ``window`` anos.

    A janela é ``[reference_year - window + 1, reference_year]``. Quando
    ``reference_year`` é ``None``, usa o maior ano presente nas obras.
    """
    years = [y for w in works if (y := _publication_year(w)) is not None]
    if not years:
        return 0
    ref = reference_year if reference_year is not None else max(years)
    min_year = ref - window + 1
    recent = [
        _citation_count(w)
        for w in works
        if (y := _publication_year(w)) is not None and min_year <= y <= ref
    ]
    return compute_h_index(recent)


def _count_concepts(works: Sequence[Mapping[str, Any]]) -> Counter:
    counter: Counter = Counter()
    for w in works:
        for c in (w.get("concepts") or w.get("topics") or []):
            if isinstance(c, dict):
                name = c.get("display_name") or c.get("wikidata")
                if name:
                    counter[name] += 1
            elif isinstance(c, str):
                counter[c] += 1
    return counter


def _count_coauthors(works: Sequence[Mapping[str, Any]]) -> Counter:
    counter: Counter = Counter()
    for w in works:
        auths = w.get("authorships") or w.get("authors") or w.get("autores") or []
        if not isinstance(auths, list):
            continue
        for a in auths:
            if isinstance(a, dict):
                author = a.get("author") or {}
                name = (
                    (author.get("display_name") if isinstance(author, dict) else None)
                    or a.get("name")
                    or a.get("display_name")
                )
                if name:
                    counter[name] += 1
            elif isinstance(a, str):
                counter[a] += 1
    return counter


def _sample_publications(works: Sequence[Mapping[str, Any]], size: int) -> list[dict]:
    sample: list[dict] = []
    for w in works:
        if len(sample) >= size:
            break
        sample.append(
            {
                "id": w.get("id") or w.get("work_id"),
                "title": w.get("title") or w.get("titulo") or w.get("name") or "",
                "year": w.get("year") or w.get("ano"),
                "doi": w.get("doi") or w.get("DOI"),
                "cited_by_count": _citation_count(w),
            }
        )
    return sample


def _author_name(node: Mapping[str, Any]) -> str | None:
    return node.get("nome") or node.get("name") or node.get("display_name")


def compute_author_metrics(
    author_id: str,
    node: Mapping[str, Any] | None,
    *,
    reference_year: int | None = None,
    sample_size: int = SAMPLE_SIZE,
    top_n: int = TOP_N,
    h5_window: int = H5_WINDOW_YEARS,
) -> dict[str, Any]:
    """Agrega as métricas de um autor a partir do nó ``autores_flat/{id}``.

    O handler de rota é responsável apenas por ler ``node`` do banco e por
    devolver 404 quando ele for vazio; toda a regra de negócio está aqui.
    """
    works = extract_works(node)
    node = node or {}

    citations = [_citation_count(w) for w in works]
    years = [y for w in works if (y := _publication_year(w)) is not None]

    return {
        "author_id": author_id,
        "name": _author_name(node),
        "publications_count": len(works),
        "total_citations": sum(citations),
        "h_index": compute_h_index(citations),
        "h5_index": compute_h5_index(works, reference_year, h5_window),
        "i10_index": compute_i10_index(citations),
        "first_year": min(years) if years else None,
        "last_year": max(years) if years else None,
        "top_concepts": _count_concepts(works).most_common(top_n),
        "top_coauthors": _count_coauthors(works).most_common(top_n),
        "sample_publications": _sample_publications(works, sample_size),
    }
