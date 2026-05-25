# functions/api_routes/harvest_authors.py
from fastapi import APIRouter, Body, HTTPException
from typing import Dict, Any, List, Optional, Tuple
import time, traceback

# --- imports dos helpers que você já tem
from functions.ingest.openalex_name import (
    search_authors_by_name,
    _pick_best_author,
    fetch_author,
    list_works_for_author,
    _save_bundle,             # salva em /openalex/{A..}/...
)

from functions.ingest.orcid_api import fetch_orcid_record
from functions.ingest.crossref_api import crossref_works_by_author
from functions.ingest.semanticscholar_api import s2_author_search, s2_author

from functions.common.dbref import ref

router = APIRouter(prefix="/harvest", tags=["Harvest (All Free Sources)"])

def _ref(path: str):
    return ref(path)

def _tail_orcid(v: Optional[str]) -> Optional[str]:
    if not v: return None
    v = v.strip()
    return v.split("/")[-1] if "/" in v else v

def _name_key(name: str) -> str:
    return (name or "").strip().lower().replace("  ", " ").replace("/", "_")

def _save_orcid(orcid: str, data: Dict[str, Any]) -> None:
    ts = str(int(time.time()))
    base = _ref(f"external/orcid/{orcid}")
    base.child("record").set(data)
    base.child("batches").child(ts).set({"record": data, "imported_at": int(ts)})
    # resumo
    name = (((data.get("person") or {}).get("name") or {}).get("display-name") or {}).get("value")
    emails = []
    for e in ((data.get("person") or {}).get("emails") or {}).get("email", []) or []:
        v = e.get("email")
        if v: emails.append(v)
    base.child("summary").update({"orcid": orcid, "display_name": name, "emails": emails, "last_import_ts": int(ts)})

def _save_crossref(name: str, items: List[Dict[str, Any]]) -> None:
    ts = str(int(time.time()))
    key = _name_key(name)
    base = _ref(f"external/crossref/by_author_name/{key}")
    base.child("batches").child(ts).set({"name": name, "items": items, "imported_at": int(ts)})
    dois = [it.get("DOI") for it in items if it.get("DOI")]
    base.child("summary").update({"name": name, "last_import_ts": int(ts), "works_count": len(items), "dois_sample": dois[:10]})

def _save_semanticscholar(author_id: str, data: Dict[str, Any]) -> None:
    ts = str(int(time.time()))
    base = _ref(f"external/semanticscholar/{author_id}")
    base.child("batches").child(ts).set({"author": data, "imported_at": int(ts)})
    base.child("summary").update({
        "author_id": author_id,
        "name": data.get("name"),
        "hIndex": data.get("hIndex"),
        "paperCount": data.get("paperCount"),
        "citationCount": data.get("citationCount"),
        "last_import_ts": int(ts)
    })

def _merge_to_autores(orcid: Optional[str], openalex_id: Optional[str], s2_id: Optional[str], crossref_name: Optional[str]) -> Dict[str, Any]:
    """reaproveita o merge do módulo autores_merge (sem expor endpoint aqui)."""
    from functions.api_routes.autores_merge import _ref as _ref_merge
    from functions.api_routes.autores_merge import _find_autor_by_orcid_tail
    autor_payload = {}
    # carrega resumos de cada fonte (se existirem) e monta o melhor payload
    if openalex_id:
        oa = _ref_merge(f"openalex/{openalex_id}/summary").get() or {}
        if oa:
            autor_payload["nome"] = oa.get("display_name") or autor_payload.get("nome")
            autor_payload["orcid"] = _tail_orcid(orcid) or _tail_orcid(oa.get("orcid"))
            autor_payload.setdefault("metrics", {})
            autor_payload["metrics"]["works_count"] = oa.get("works_count")
            autor_payload["metrics"]["cited_by_count"] = oa.get("cited_by_count")
            autor_payload["openalex_author_id"] = openalex_id
    if orcid:
        oc = _ref_merge(f"external/orcid/{_tail_orcid(orcid)}/summary").get() or {}
        if oc:
            autor_payload["nome"] = oc.get("display_name") or autor_payload.get("nome")
            autor_payload["orcid"] = _tail_orcid(orcid)
    if s2_id:
        s2 = _ref_merge(f"external/semanticscholar/{s2_id}/summary").get() or {}
        if s2:
            autor_payload["nome"] = s2.get("name") or autor_payload.get("nome")
            autor_payload.setdefault("metrics", {})
            autor_payload["metrics"]["hIndex"] = s2.get("hIndex")
            autor_payload["metrics"]["paperCount"] = s2.get("paperCount")
            autor_payload["metrics"]["citationCount"] = s2.get("citationCount")
            autor_payload["semanticscholar_author_id"] = s2_id
    if crossref_name:
        cr = _ref_merge(f"external/crossref/by_author_name/{_name_key(crossref_name)}/summary").get() or {}
        if cr:
            autor_payload.setdefault("metrics", {})
            autor_payload["metrics"]["crossref_works_count"] = cr.get("works_count")

    if not autor_payload:
        raise HTTPException(400, "Nenhum dado encontrado para consolidar em /autores.")

    autores_ref = _ref_merge("autores")
    autor_id = None
    if autor_payload.get("orcid"):
        autor_id = _find_autor_by_orcid_tail(autor_payload.get("orcid"))
    if autor_id:
        autores_ref.child(autor_id).update(autor_payload | {"updated_at": int(time.time())})
    else:
        autor_id = autores_ref.push().key
        autores_ref.child(autor_id).set(autor_payload | {"created_at": int(time.time())})

    # links de fontes
    fontes = {}
    if openalex_id: fontes["openalex_author_id"] = openalex_id
    if orcid: fontes["orcid"] = _tail_orcid(orcid)
    if s2_id: fontes["semanticscholar_author_id"] = s2_id
    if crossref_name: fontes["crossref_name_key"] = _name_key(crossref_name)
    autores_ref.child(autor_id).child("sources").update(fontes)

    return {"autor_id": autor_id, "merged_fields": autor_payload, "sources": fontes}

@router.post("/batch", summary="Harvester completo em lote (OpenAlex + ORCID + Crossref + Semantic Scholar + /autores)")
def harvest_batch(body: Dict[str, Any] = Body(
    ...,
    example={
        "items": [
            {"name": "Diego Luis Kreutz"},
            {"name": "Gilleanes Thorwald Araujo Guedes", "prefer_orcid": "0000-0001-5457-2600"},
            {"name": "Silvio E. Quincozes", "prefer_orcid": "0000-0001-6793-4033"}
        ],
        "max_works_pages": 3,
        "s2_limit": 5,
        "crossref_rows": 100,
        "also_merge_autores": True
    }
)):
    """
    items: lista de objetos com:
      - name (obrigatório)
      - prefer_orcid (opcional): ajuda a escolher o autor certo no OpenAlex
      - prefer_s2_author_id (opcional): se já souber o ID do Semantic Scholar
    max_works_pages: limitar paginação de /works do OpenAlex (200/pg)
    s2_limit: quantos candidatos no author_search do S2
    crossref_rows: quantos itens do Crossref por nome
    also_merge_autores: se True, consolida em /autores ao final
    """
    try:
        items: List[Dict[str, Any]] = body.get("items") or []
        if not items:
            raise HTTPException(400, "Envie 'items': [{\"name\": \"...\"}, ...]")

        max_pages = int(body.get("max_works_pages", 3))
        s2_limit = int(body.get("s2_limit", 5))
        crossref_rows = int(body.get("crossref_rows", 100))
        also_merge = bool(body.get("also_merge_autores", True))

        results: List[Dict[str, Any]] = []

        for it in items:
            name = (it.get("name") or "").strip()
            prefer_orcid = _tail_orcid(it.get("prefer_orcid"))
            prefer_s2_id = (it.get("prefer_s2_author_id") or "").strip() or None

            if not name:
                results.append({"name": name, "status": "SKIPPED_EMPTY"})
                continue

            out: Dict[str, Any] = {"name": name}

            # --- ORCID (se informado) ---
            if prefer_orcid:
                try:
                    oc = fetch_orcid_record(prefer_orcid)
                    _save_orcid(prefer_orcid, oc)
                    out["orcid_saved"] = True
                except Exception as e:
                    out["orcid_error"] = str(e)

            # --- OpenAlex: escolher melhor autor e salvar /works ---
            try:
                found = search_authors_by_name(name, per_page=15)
                best = _pick_best_author(found.get("results", []), prefer_orcid=prefer_orcid)
                if not best:
                    out["status"] = "OPENALEX_NOT_FOUND"
                    results.append(out)
                    continue

                # baixa perfil completo + obras
                full = fetch_author(best["id"])  # nossa função já normaliza para API
                works_url = full.get("works_api_url")
                works = list_works_for_author(works_url, max_pages=max_pages) if works_url else []
                author_id, batch_id = _save_bundle(full, works)

                out.update({
                    "openalex_author_id": author_id,
                    "display_name": full.get("display_name"),
                    "openalex_works_saved": len(works),
                    "openalex_batch_id": batch_id,
                    "openalex_rt_path": f"/openalex/{author_id}/batches/{batch_id}"
                })
            except Exception as e:
                out["openalex_error"] = str(e)

            # --- Crossref por nome ---
            try:
                cr = crossref_works_by_author(name, rows=crossref_rows)
                items_cr = (cr.get("message") or {}).get("items", [])
                _save_crossref(name, items_cr)
                out["crossref_works"] = len(items_cr)
            except Exception as e:
                out["crossref_error"] = str(e)

            # --- Semantic Scholar: buscar e importar ---
            s2_id_used: Optional[str] = None
            try:
                if prefer_s2_id:
                    data = s2_author(prefer_s2_id, with_papers=True, papers_limit=200)
                    _save_semanticscholar(prefer_s2_id, data)
                    s2_id_used = prefer_s2_id
                else:
                    search = s2_author_search(name, limit=s2_limit)
                    hits = (search.get("data") or []) if isinstance(search, dict) else []
                    if hits:
                        # heurística simples: maior citationCount, depois paperCount
                        hits_sorted = sorted(
                            hits,
                            key=lambda a: (a.get("citationCount") or 0, a.get("paperCount") or 0),
                            reverse=True
                        )
                        s2_id_used = str(hits_sorted[0].get("authorId"))
                        data = s2_author(s2_id_used, with_papers=True, papers_limit=200)
                        _save_semanticscholar(s2_id_used, data)
                if s2_id_used:
                    out["semanticscholar_author_id"] = s2_id_used
            except Exception as e:
                out["semanticscholar_error"] = str(e)

            # --- Merge final em /autores ---
            if also_merge:
                try:
                    merged = _merge_to_autores(
                        orcid=prefer_orcid,
                        openalex_id=out.get("openalex_author_id"),
                        s2_id=s2_id_used,
                        crossref_name=name
                    )
                    out["autor_id"] = merged.get("autor_id")
                    out["status"] = "IMPORTED_AND_MERGED"
                except Exception as e:
                    out["merge_error"] = str(e)
                    out["status"] = "IMPORTED"
            else:
                out["status"] = "IMPORTED"

            results.append(out)

        return {"ok": True, "items": results}

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Falha no harvest_batch: {e}")
