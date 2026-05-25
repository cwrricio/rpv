"""Testes unitários de services/analytics.py (Frente 4.3).

Cobrem as funções puras de métricas bibliométricas com conjuntos de publicações
de citações conhecidas. Nenhum acesso ao Firebase.
"""

import pytest

from functions.services.analytics import (
    compute_author_metrics,
    compute_h5_index,
    compute_h_index,
    compute_i10_index,
    extract_works,
)


# --------------------------------------------------------------------------- #
# h-index
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "citations, expected",
    [
        ([], 0),
        ([0, 0, 0], 0),
        ([3, 3, 3], 3),
        ([10, 8, 5, 4, 3], 4),   # 4 obras com >=4 citações; a 5ª tem só 3
        ([1, 1, 1, 1], 1),
        ([100], 1),
        ([5, 5, 5, 5, 5], 5),
    ],
)
def test_compute_h_index(citations, expected):
    assert compute_h_index(citations) == expected


def test_h_index_ignora_ordem():
    assert compute_h_index([4, 10, 3, 8, 5]) == 4


# --------------------------------------------------------------------------- #
# i10-index
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "citations, expected",
    [
        ([], 0),
        ([10, 9, 11, 10, 2], 3),     # 10, 11, 10
        ([9, 9, 9], 0),
        ([10, 10, 10], 3),
    ],
)
def test_compute_i10_index(citations, expected):
    assert compute_i10_index(citations) == expected


def test_i10_index_limiar_customizado():
    assert compute_i10_index([5, 5, 1], threshold=5) == 2


# --------------------------------------------------------------------------- #
# h5-index
# --------------------------------------------------------------------------- #
def test_h5_index_filtra_por_janela_de_anos():
    works = [
        {"year": 2024, "cited_by_count": 10},
        {"year": 2023, "cited_by_count": 8},
        {"year": 2022, "cited_by_count": 5},
        # fora da janela [2020, 2024] com reference_year=2024, window=5:
        {"year": 2015, "cited_by_count": 100},
    ]
    # Considera apenas 2020..2024 -> citações [10, 8, 5] -> h=3
    assert compute_h5_index(works, reference_year=2024, window=5) == 3


def test_h5_index_usa_ano_mais_recente_quando_sem_referencia():
    works = [
        {"year": 2024, "cited_by_count": 10},
        {"year": 2024, "cited_by_count": 9},
        {"year": 2010, "cited_by_count": 50},  # fora da janela 2020..2024
    ]
    assert compute_h5_index(works, window=5) == 2


def test_h5_index_sem_anos_retorna_zero():
    assert compute_h5_index([{"cited_by_count": 10}]) == 0


# --------------------------------------------------------------------------- #
# extract_works
# --------------------------------------------------------------------------- #
def test_extract_works_formato_mapa_ignora_sentinela():
    node = {"works": {"w1": {"title": "A"}, "_": "sentinela", "w2": {"title": "B"}}}
    works = extract_works(node)
    assert {w["title"] for w in works} == {"A", "B"}
    assert all("id" in w for w in works)


def test_extract_works_formato_lista():
    node = {"works": [{"title": "A"}, {"title": "B"}]}
    assert len(extract_works(node)) == 2


def test_extract_works_node_vazio_ou_none():
    assert extract_works(None) == []
    assert extract_works({}) == []
    assert extract_works({"works": "lixo"}) == []


# --------------------------------------------------------------------------- #
# compute_author_metrics — agregação completa
# --------------------------------------------------------------------------- #
@pytest.fixture
def node_exemplo():
    return {
        "nome": "Maria Silva",
        "works": {
            "w1": {
                "title": "Aprendizado de Máquina",
                "year": 2020,
                "cited_by_count": 10,
                "concepts": [{"display_name": "ML"}],
                "authorships": [
                    {"author": {"display_name": "Maria Silva"}},
                    {"author": {"display_name": "João"}},
                ],
            },
            "w2": {
                "title": "PLN aplicado",
                "year": 2021,
                "cited_by_count": 5,
                "concepts": [{"display_name": "ML"}, {"display_name": "NLP"}],
                "authorships": [{"author": {"display_name": "João"}}],
            },
            "w3": {
                "title": "Estudo antigo",
                "year": 2019,
                "cited_by_count": 2,
            },
            "_": "sentinela ignorada",
        },
    }


def test_compute_author_metrics_agrega_corretamente(node_exemplo):
    m = compute_author_metrics("A123", node_exemplo)

    assert m["author_id"] == "A123"
    assert m["name"] == "Maria Silva"
    assert m["publications_count"] == 3            # "_" ignorado
    assert m["total_citations"] == 17              # 10 + 5 + 2
    assert m["h_index"] == 2                        # [10,5,2] -> 2
    assert m["i10_index"] == 1                      # só 10 >= 10
    assert m["h5_index"] == 2                       # janela cobre tudo -> h([10,5,2])
    assert m["first_year"] == 2019
    assert m["last_year"] == 2021
    assert m["top_concepts"] == [("ML", 2), ("NLP", 1)]
    assert ("João", 2) in m["top_coauthors"]
    assert ("Maria Silva", 1) in m["top_coauthors"]
    assert len(m["sample_publications"]) == 3


def test_compute_author_metrics_node_vazio():
    m = compute_author_metrics("X", {})
    assert m["publications_count"] == 0
    assert m["total_citations"] == 0
    assert m["h_index"] == 0
    assert m["h5_index"] == 0
    assert m["i10_index"] == 0
    assert m["first_year"] is None
    assert m["last_year"] is None
    assert m["top_concepts"] == []
    assert m["sample_publications"] == []


def test_sample_publications_respeita_limite():
    works = {f"w{i}": {"title": f"T{i}", "year": 2020, "cited_by_count": i} for i in range(25)}
    m = compute_author_metrics("X", {"works": works}, sample_size=10)
    assert len(m["sample_publications"]) == 10
    assert m["publications_count"] == 25
