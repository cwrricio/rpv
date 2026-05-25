# functions/api_routes/autores_flat.py
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional, List, Tuple
import time, re
from datetime import datetime
from functions.common.dbref import ref

# Reaproveita utilitários do seu módulo OpenAlex
from functions.ingest.openalex_name import (
    search_authors_by_name,
    _pick_best_author,
    fetch_author,
    list_works_for_author,  # (works_url, max_pages) -> List[dict]
    _save_bundle,           # (author_dict, works_list) -> (author_id, batch_ts)
)

router = APIRouter(prefix="/autores_flat", tags=["Autores • Flat por nome"])

# ---------- Firebase helpers ----------
def _ref(path: str):
    return ref(path)

# ---------- Strings & keys ----------
def _slug_nome(nome: str) -> str:
    s = (nome or "").strip().lower()
    rep = {
        "á":"a","à":"a","â":"a","ã":"a","ä":"a",
        "é":"e","è":"e","ê":"e","ë":"e",
        "í":"i","ì":"i","î":"i","ï":"i",
        "ó":"o","ò":"o","ô":"o","õ":"o","ö":"o",
        "ú":"u","ù":"u","û":"u","ü":"u",
        "ç":"c"
    }
    for k,v in rep.items(): s = s.replace(k,v)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s

def _tail(v: Optional[str]) -> Optional[str]:
    if not v: return None
    v = v.strip().strip(".")
    return v.split("/")[-1] if "/" in v else v

# ---------- Coleta & normalização ----------
def _collect_all_works(oa_id: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Junta TODAS as obras já salvas em /openalex/{oa_id}/batches/*/works."""
    if not oa_id:
        return {}
    batches = _ref(f"openalex/{oa_id}/batches").get() or {}
    merged: Dict[str, Dict[str, Any]] = {}
    for bkey in sorted(batches.keys()):
        works = (batches[bkey] or {}).get("works") or {}
        for wid, w in (works or {}).items():
            work_id = wid or _tail(w.get("id")) or _tail(w.get("workId")) or f"auto_{len(merged)+1}"
            merged[work_id] = _normalize_work(work_id, w)
    return merged

def _normalize_work(work_id: str, w: Dict[str, Any]) -> Dict[str, Any]:
    # Campos frequentes do OpenAlex; mantenha simples e “flat”
    def _best_url():
        doi = w.get("doi")
        if doi:
            return doi if str(doi).startswith("http") else f"https://doi.org/{str(doi).replace('doi:','')}"
        pl = (w.get("primary_location") or {})
        if pl.get("landing_page_url"):
            return pl["landing_page_url"]
        hv = (w.get("host_venue") or {})
        return hv.get("url")

    hv = w.get("host_venue") or {}
    return {
        "id": work_id,
        "title": w.get("title") or w.get("display_name"),
        "type": w.get("type"),
        "year": w.get("year") or w.get("publication_year"),
        "doi": _tail(w.get("doi")),
        "url": _best_url(),
        "venue": hv.get("display_name") or (w.get("venue") if isinstance(w.get("venue"), str) else None),
        "cited_by_count": w.get("cited_by_count") or 0,
        "open_access": (w.get("open_access") or {}),
        "concepts": [c.get("display_name") for c in sorted((w.get("concepts") or []), key=lambda c: c.get("score",0), reverse=True)],
        "authorships": _normalize_authorships(w.get("authorships") or [])
    }

def _normalize_authorships(auths: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = []
    for a in auths:
        insts = []
        for i in a.get("institutions") or []:
            insts.append({
                "id": _tail(i.get("id")),
                "display_name": i.get("display_name"),
                "country_code": i.get("country_code"),
            })
        out.append({
            "author_id": _tail((a.get("author") or {}).get("id")),
            "author_name": (a.get("author") or {}).get("display_name"),
            "raw_author_name": a.get("raw_author_name"),
            "author_position": a.get("author_position"),
            "institutions": insts
        })
    return out

def _summarize_profile(author: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "openalex_author_id": _tail(author.get("id")),
        "display_name": author.get("display_name"),
        "display_name_alternatives": author.get("display_name_alternatives"),
        "orcid": _tail(author.get("orcid")),
        "works_count": author.get("works_count"),
        "cited_by_count": author.get("cited_by_count"),
        "summary_stats": author.get("summary_stats"),
        "last_known_institutions": author.get("last_known_institutions"),
        "affiliations": author.get("affiliations"),
        "topics": author.get("topics"),
        "ids": {
            "openalex": _tail((author.get("ids") or {}).get("openalex")),
            "orcid": _tail((author.get("ids") or {}).get("orcid")),
            "mag": (author.get("ids") or {}).get("mag"),
            "wikidata": (author.get("ids") or {}).get("wikidata"),
            "wikipedia": (author.get("ids") or {}).get("wikipedia"),
        },
        "created_date": author.get("created_date"),
        "updated_date": author.get("updated_date"),
    }

# ---------- índices ----------
def _compute_h_index(citations: List[int]) -> int:
    c = sorted((x for x in citations if isinstance(x,int)), reverse=True)
    h=0
    for i, v in enumerate(c, start=1):
        if v >= i: h = i
        else: break
    return h

def _compute_i_k_index(citations: List[int], k: int) -> int:
    return sum(1 for v in citations if isinstance(v,int) and v >= k)

def _compute_h5_index(works: Dict[str, Dict[str, Any]]) -> int:
    if not works: return 0
    y = datetime.now().year
    recent = sorted([(w.get("cited_by_count") or 0)
                     for w in works.values()
                     if isinstance(w.get("year"), int) and w["year"] >= y-5],
                    reverse=True)
    h5=0
    for i,v in enumerate(recent, start=1):
        if v >= i: h5 = i
        else: break
    return h5

# ---------- gravações “flat” + coleção /autores ----------
def _write_autores_entry(profile: Dict[str, Any]) -> str:
    """Cria/atualiza /autores/{openalex_author_id} com dados básicos do autor."""
    oa_id = profile.get("openalex_author_id")
    if not oa_id:
        raise RuntimeError("openalex_author_id ausente para /autores.")
    entry = {
        "id": oa_id,
        "nome": profile.get("display_name"),
        "orcid": profile.get("orcid"),
        "openalex_author_id": oa_id,
        "works_count": profile.get("works_count"),
        "cited_by_count": profile.get("cited_by_count"),
        "updated_at": int(time.time()),
    }
    _ref(f"autores/{oa_id}").update(entry)
    return oa_id

def _write_flat(nome: str, author: Dict[str, Any], works: Dict[str, Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    slug = _slug_nome(nome)
    profile = _summarize_profile(author)

    # Cabeçalho base
    base = _ref(f"autores_flat/{slug}")
    base.update({
        "nome": nome,
        "ids": profile.get("ids"),
        "profile": {k: v for k, v in profile.items() if k not in ("ids",)},  # profile “clean”
        "updated_at": int(time.time())
    })

    # Works (flat, sem subpastas)
    base.child("works").set(works)

    # Métricas
    citations = [ (w.get("cited_by_count") or 0) for w in works.values() ]
    metrics = {
        "works_count": profile.get("works_count"),
        "cited_by_count": profile.get("cited_by_count"),
        # do OpenAlex, se vier
        "h_index_openalex": ((profile.get("summary_stats") or {}).get("h_index")),
        "i10_index_openalex": ((profile.get("summary_stats") or {}).get("i10_index")),
        # calculados:
        "h_index_calc": _compute_h_index(citations),
        "i10_index_calc": _compute_i_k_index(citations, 10),
        "i5_index_calc": _compute_i_k_index(citations, 5),
        "h5_index_calc": _compute_h5_index(works),
    }
    base.child("metrics").update({k:v for k,v in metrics.items() if v is not None})

    # affiliations e topics “de cima” (se quiserem fácil no flat)
    base.child("affiliations").set(profile.get("affiliations") or [])
    base.child("topics").set(profile.get("topics") or [])

    # também mantém uma referência agregada em /autores
    _write_autores_entry(profile)

    return slug, metrics

# ---------- fluxo completo: importar do OpenAlex + gravar tudo ----------
def _import_openalex_by_name_or_orcid(name: str, prefer_orcid: Optional[str], max_pages: Optional[int]) -> Tuple[Dict[str,Any], Dict[str,Any], List[Dict[str,Any]]]:
    """Busca autor no OpenAlex (forçando ORCID se houver), baixa perfil+obras, salva em /openalex e retorna (author, saved_summary, works_list)."""
    found = search_authors_by_name(name, per_page=15)
    best = _pick_best_author(found.get("results", []), prefer_orcid=prefer_orcid)
    if not best:
        raise HTTPException(404, f"Nenhum autor encontrado para: {name}")

    full = fetch_author(best["id"])  # dict completo do autor
    works_url = full.get("works_api_url")
    works_list = list_works_for_author(works_url, max_pages=max_pages) if works_url else []

    # salva “cru” em /openalex/{id}/summary + /batches/{ts}/works
    _save_bundle(full, works_list)
    return full, (full.get("summary_stats") or {}), works_list

# ------------------ ENDPOINT: 1 autor ------------------
@router.post("/generate", summary="Importa do OpenAlex, salva tudo e gera flat por nome (com works, profile, tópicos, métricas)")
def generate_flat(body: Dict[str, Any] = Body(..., example={
    "nome": "Silvio E. Quincozes",
    "prefer_orcid": "0000-0001-6793-4033",
    "max_pages": 5
})):
    nome = (body.get("nome") or "").strip()
    prefer_orcid = _tail(body.get("prefer_orcid"))
    max_pages = body.get("max_pages")
    if not nome:
        raise HTTPException(400, "Campo 'nome' é obrigatório.")

    # importa do OpenAlex e salva /openalex
    author, _, _ = _import_openalex_by_name_or_orcid(nome, prefer_orcid, max_pages)

    # lê tudo salvo e gera flat COMPLETO
    oa_id = _tail(author.get("id"))
    works = _collect_all_works(oa_id)
    slug, metrics = _write_flat(nome, author, works)

    return {
        "ok": True,
        "openalex_author_id": oa_id,
        "flat_path": f"/autores_flat/{slug}",
        "autores_ref": f"/autores/{oa_id}",
        "works_count_flat": len(works),
        "metrics": metrics
    }

# ------------------ ENDPOINT: lote ------------------
@router.post("/batch_generate", summary="Importa (por nome+ORCID) vários autores, salva tudo e gera flat para cada")
def batch_generate(body: Dict[str, Any] = Body(..., example={
    "items": [
        {"name":"Claudio Schepke","orcid":"0000-0003-4118-8831"},
        {"name":"Diego Luis Kreutz","orcid":"0000-0003-0830-0238"}
    ],
    "max_pages": 5
})):
    items = body.get("items") or []
    max_pages = body.get("max_pages")
    if not items:
        raise HTTPException(400, "Envie 'items' com ao menos um autor.")

    results = []
    for it in items:
        nome = (it.get("name") or "").strip()
        prefer_orcid = _tail(it.get("orcid"))
        if not nome:
            results.append({"name": None, "status": "SKIPPED_NO_NAME"})
            continue

        try:
            author, _, _ = _import_openalex_by_name_or_orcid(nome, prefer_orcid, max_pages)
            oa_id = _tail(author.get("id"))
            works = _collect_all_works(oa_id)
            slug, metrics = _write_flat(nome, author, works)
            results.append({
                "name": nome,
                "openalex_author_id": oa_id,
                "flat_path": f"/autores_flat/{slug}",
                "autores_ref": f"/autores/{oa_id}",
                "works_count_flat": len(works),
                "metrics": metrics,
                "status": "OK"
            })
        except HTTPException as he:
            results.append({"name": nome, "status": f"ERROR_{he.status_code}", "detail": he.detail})
        except Exception as e:
            results.append({"name": nome, "status": "ERROR_500", "detail": str(e)})

    return {"processed": len(results), "results": results}
