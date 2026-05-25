# functions/http/autores.py
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from functions.crud.autor_crud import AutorCRUD
from functions.crud.produto_crud import ProdutoCRUD

router = APIRouter(tags=["Autores"])  # prefix definido no main.py

_crud: Optional[AutorCRUD] = None
def crud() -> AutorCRUD:
    global _crud
    if _crud is None:
        _crud = AutorCRUD()
    return _crud

@router.get("/", summary="Listar autores")
def listar(svc: AutorCRUD = Depends(crud)):
    return svc.list()

@router.post("/", status_code=201, summary="Criar autor")
def criar(body: dict, svc: AutorCRUD = Depends(crud)):
    if not isinstance(body, dict):
        raise HTTPException(400, "Body inválido")
    return svc.create(body)

@router.get("/{id}", summary="Obter autor")
def obter(id: str, svc: AutorCRUD = Depends(crud)):
    item = svc.get(id)
    if not item:
        raise HTTPException(404, "Autor não encontrado")
    return item

@router.patch("/{id}", summary="Atualizar autor")
def atualizar(id: str, body: dict, svc: AutorCRUD = Depends(crud)):
    upd = svc.update(id, body)
    if not upd:
        raise HTTPException(404, "Autor não encontrado")
    return upd

@router.delete("/{id}", status_code=204, summary="Remover autor")
def remover(id: str, svc: AutorCRUD = Depends(crud)):
    ok = svc.delete(id)
    if not ok:
        raise HTTPException(404, "Autor não encontrado")
    return

# versão única e consolidada do endpoint /{id}/produtos
@router.get("/{id}/produtos", summary="Listar produções de um autor")
def listar_produtos_do_autor(id: str, svc: AutorCRUD = Depends(crud)):
    """
    Retorna as produções relacionadas a um autor identificado por `id`.
    O `id` pode ser a chave RTDB do autor ou um ORCID.
    """
    autor = svc.get(id)
    if not autor:
        all_authors = svc.list()
        autor = next((a for a in all_authors if (a.get("orcid") or "").strip() == id.strip()), None)

    if not autor:
        raise HTTPException(404, "Autor não encontrado")

    # usar ProdutoCRUD para obter produções
    prod_crud = ProdutoCRUD()
    produtos = prod_crud.list()

    # coletar ids associados ao autor
    ids = set()
    if autor.get("produto_id"):
        ids.add(autor.get("produto_id"))
    if autor.get("produto_ids") and isinstance(autor.get("produto_ids"), list):
        ids.update(autor.get("produto_ids"))

    matched = []
    name_lower = (autor.get("nome") or autor.get("name") or "").strip().lower()
    for p in produtos:
        pid = p.get("id") or p.get("_id")
        if pid and pid in ids:
            matched.append(p)
            continue
        autores_field = p.get("autores")
        if autores_field:
            if isinstance(autores_field, list):
                if any((a or "").strip().lower() == name_lower for a in autores_field):
                    matched.append(p)
                    continue
            elif isinstance(autores_field, str):
                parts = [s.strip().lower() for s in autores_field.split(",") if s.strip()]
                if name_lower in parts:
                    matched.append(p)
                    continue

    return matched


@router.get("/{id}/metrics", summary="Métricas agregadas de um autor")
def obter_metricas_autor(id: str, svc: AutorCRUD = Depends(crud)):
    """
    Retorna métricas agregadas para um autor identificado por `id` (chave RTDB ou ORCID).
    Métricas calculadas (quando possível):
      - publications_count
      - total_citations
      - h_index
      - first_year, last_year
      - top_concepts (lista com contagens)
      - top_coauthors (lista com contagens)
      - sample_publications (até 10 publicações com campos básicos)
    """
    autor = svc.get(id)
    if not autor:
        all_authors = svc.list()
        autor = next((a for a in all_authors if (a.get("orcid") or "").strip() == id.strip()), None)

    if not autor:
        raise HTTPException(404, "Autor não encontrado")

    # tenta usar works embutidos no autor
    works = []
    wnode = autor.get("works") or autor.get("work") or autor.get("publications")
    if wnode:
        if isinstance(wnode, dict):
            works = [{"id": k, **v} for k, v in wnode.items() if k != "_"]
        elif isinstance(wnode, list):
            works = wnode

    # fallback: varrer produtos e filtrar por autor (igual lógica do endpoint produtos)
    if not works:
        prod_crud = ProdutoCRUD()
        produtos = prod_crud.list()
        name_lower = (autor.get("nome") or autor.get("name") or "").strip().lower()
        matched = []
        for p in produtos:
            pid = p.get("id") or p.get("_id")
            autores_field = p.get("autores")
            matched_by_name = False
            if autores_field:
                if isinstance(autores_field, list):
                    if any((str(a or "").strip().lower() == name_lower) for a in autores_field):
                        matched_by_name = True
                elif isinstance(autores_field, str):
                    parts = [s.strip().lower() for s in autores_field.split(",") if s.strip()]
                    if name_lower in parts:
                        matched_by_name = True
            if matched_by_name:
                matched.append(p)
        works = matched

    # agregações
    publications_count = len(works)
    citation_list = []
    year_list = []
    concept_counts = {}
    coauthor_counts = {}

    author_name_lower = (autor.get("nome") or autor.get("name") or "").strip().lower()

    for w in works:
        # citar campos possíveis
        cited = w.get("cited_by_count") or w.get("cited") or w.get("citations") or 0
        try:
            c = int(cited)
        except Exception:
            c = 0
        citation_list.append(c)

        yr = w.get("year") or w.get("ano")
        try:
            if yr is not None:
                year_list.append(int(yr))
        except Exception:
            pass

        concepts = w.get("concepts") or w.get("topics") or []
        if isinstance(concepts, list):
            for cc in concepts:
                concept_counts[cc] = concept_counts.get(cc, 0) + 1

        authorships = w.get("authorships") or w.get("autores") or []
        if isinstance(authorships, list):
            for au in authorships:
                if isinstance(au, dict):
                    name = (au.get("author_name") or au.get("name") or "").strip()
                else:
                    name = str(au or "").strip()
                if name and name.lower() != author_name_lower:
                    coauthor_counts[name] = coauthor_counts.get(name, 0) + 1

    total_citations = sum(citation_list)

    # h-index
    h_index = 0
    citation_list_sorted = sorted(citation_list, reverse=True)
    for i, val in enumerate(citation_list_sorted, start=1):
        if val >= i:
            h_index = i
        else:
            break

    first_year = min(year_list) if year_list else None
    last_year = max(year_list) if year_list else None

    top_concepts = sorted(concept_counts.items(), key=lambda x: -x[1])[:10]
    top_coauthors = sorted(coauthor_counts.items(), key=lambda x: -x[1])[:10]

    # sample publications (básico)
    sample_publications = []
    for w in works[:10]:
        sample_publications.append({
            "id": w.get("id") or w.get("_id"),
            "title": w.get("title") or w.get("titulo") or w.get("name"),
            "year": w.get("year") or w.get("ano"),
            "cited_by_count": w.get("cited_by_count") or w.get("citations") or 0,
            "doi": w.get("doi") or w.get("DOI") or None,
        })

    return {
        "author_id": autor.get("id") or autor.get("_id") or id,
        "name": autor.get("nome") or autor.get("name"),
        "publications_count": publications_count,
        "total_citations": total_citations,
        "h_index": h_index,
        "first_year": first_year,
        "last_year": last_year,
        "top_concepts": top_concepts,
        "top_coauthors": top_coauthors,
        "sample_publications": sample_publications,
    }
