# functions/ingest/openalex_ingest_only.py
from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, Any, List, Tuple
import time, requests, traceback
from config.settings import settings
from functions.common.dbref import ref

router = APIRouter(tags=["OpenAlex Ingest Only"])
OPENALEX_BASE = "https://api.openalex.org"

def _mailto() -> str:
    return (settings.OPENALEX_MAILTO or "").strip()

def _ua_headers() -> Dict[str, str]:
    mailto = _mailto()
    return {"User-Agent": f"poshboard/0.1 (mailto:{mailto})" if mailto else "poshboard/0.1", "From": mailto or "", "Accept": "application/json"}

def http_get(url: str, params: Dict[str, Any] | None = None, timeout: int = 25) -> Dict[str, Any]:
    params = dict(params or {})
    if _mailto(): params.setdefault("mailto", _mailto())
    r = requests.get(url, params=params, headers=_ua_headers(), timeout=timeout, allow_redirects=False)
    if r.is_redirect or r.is_permanent_redirect: raise HTTPException(502, f"redirect {r.status_code} → {r.headers.get('Location','')}")
    if not (200 <= r.status_code < 300): raise HTTPException(502, f"{r.status_code}: {r.text[:300].replace('\\n',' ')}")
    if "json" not in (r.headers.get("Content-Type","").lower()): raise HTTPException(502, f"content-type '{r.headers.get('Content-Type')}'")
    return r.json()

def search_authors_by_name(name: str, per_page: int = 10) -> Dict[str, Any]:
    return http_get(f"{OPENALEX_BASE}/authors", params={"search": name, "per_page": per_page})

def fetch_author(author_id_or_url: str) -> Dict[str, Any]:
    url = author_id_or_url if author_id_or_url.startswith("http") else f"{OPENALEX_BASE}/authors/{author_id_or_url}"
    return http_get(url)

def list_works_for_author(works_url: str, max_pages: int | None = None) -> List[Dict[str, Any]]:
    works: List[Dict[str, Any]] = []
    params = {"per_page": 200, "cursor": "*"}
    pages = 0
    while True:
        page = http_get(works_url, params=params)
        for w in page.get("results", []):
            works.append({
                "workId": (w.get("id") or "").split("/")[-1] or None,
                "title": w.get("display_name"),
                "year": w.get("publication_year"),
                "doi": w.get("doi"),
            })
        pages += 1
        next_cursor = page.get("meta", {}).get("next_cursor")
        if not next_cursor or (max_pages and pages >= max_pages): break
        params["cursor"] = next_cursor
        time.sleep(0.2)
    return works

def _root_openalex():
    return ref("openalex")

def _save_bundle(author: Dict[str, Any], works: List[Dict[str, Any]]) -> Tuple[str, str]:
    author_id = (author.get("id") or "").split("/")[-1]
    if not author_id: raise RuntimeError("Author sem ID")
    ts = str(int(time.time()))
    _root_openalex().child(author_id).child("batches").child(ts).set({
        "author": author,
        "works": { (w["workId"] or f"auto_{i}"): w for i, w in enumerate(works) },
        "imported_at": int(ts),
    })
    _root_openalex().child(author_id).child("summary").update({
        "author_id": author_id,
        "display_name": author.get("display_name"),
        "last_import_ts": int(ts),
    })
    return author_id, ts

@router.get("/author_by_name", summary="Buscar autor por nome (ingest-only, sem salvar)")
def author_by_name(q: str = Query(...)):
    return search_authors_by_name(q, per_page=5)

@router.post("/by_name_ingest_only", summary="Importar por nome e salvar em /openalex (ingest-only)")
def by_name_ingest_only(body: Dict[str, Any] = Body(..., example={"name":"Alice","max_pages":5})):
    try:
        name = (body.get("name") or "").strip()
        max_pages = body.get("max_pages")
        if not name: raise HTTPException(400, "Campo 'name' é obrigatório")
        found = search_authors_by_name(name, per_page=1)
        if not found.get("results"): raise HTTPException(404, f"Nenhum autor encontrado para: {name}")
        full = fetch_author(found["results"][0]["id"])
        works = list_works_for_author(full.get("works_api_url",""), max_pages=max_pages) if full.get("works_api_url") else []
        author_id, batch_id = _save_bundle(full, works)
        return {"author_id": author_id, "works_saved": len(works), "batch_id": batch_id, "rt_db_path": f"/openalex/{author_id}/batches/{batch_id}"}
    except HTTPException: raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Falha no ingest-only: {e}")
