# functions/ingest/openalex_orcid.py
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List, Optional, Tuple
import time, requests, traceback
from config.settings import settings
from functions.common.dbref import ref

router = APIRouter(tags=["OpenAlex ORCID"])
OPENALEX_BASE = "https://api.openalex.org"

# --- HTTP helpers (mesmos do outro arquivo) ---
def _mailto() -> str:
    return (settings.OPENALEX_MAILTO or "").strip()

def _ua_headers() -> Dict[str, str]:
    mailto = _mailto()
    return {
        "User-Agent": f"poshboard/0.1 (mailto:{mailto})" if mailto else "poshboard/0.1",
        "From": mailto or "",
        "Accept": "application/json",
    }

def http_get(url: str, params: Dict[str, Any] | None = None, timeout: int = 25) -> Dict[str, Any]:
    params = dict(params or {})
    if _mailto():
        params.setdefault("mailto", _mailto())
    r = requests.get(url, params=params, headers=_ua_headers(), timeout=timeout, allow_redirects=False)
    if r.is_redirect or r.is_permanent_redirect:
        raise HTTPException(502, f"OpenAlex redirect {r.status_code} → {r.headers.get('Location','')}")
    if not (200 <= r.status_code < 300):
        raise HTTPException(502, f"OpenAlex {r.status_code}: {r.text[:300].replace('\\n',' ')}")
    if "json" not in (r.headers.get("Content-Type","").lower()):
        raise HTTPException(502, f"OpenAlex content-type '{r.headers.get('Content-Type')}'")
    return r.json()

def get_author_by_orcid(orcid: str) -> Optional[Dict[str, Any]]:
    oid = orcid.split("/")[-1]
    data = http_get(f"{OPENALEX_BASE}/authors", params={"filter": f"orcid:{oid}", "per_page": 1})
    res = data.get("results", [])
    return res[0] if res else None

def list_works_for_author(works_url: str) -> List[Dict[str, Any]]:
    works: List[Dict[str, Any]] = []
    params = {"per_page": 200, "cursor": "*"}
    while True:
        page = http_get(works_url, params=params)
        for w in page.get("results", []):
            works.append({
                "workId": (w.get("id") or "").split("/")[-1] or None,
                "title": w.get("display_name"),
                "type": w.get("type") or None,
                "year": w.get("publication_year"),
                "doi": w.get("doi"),
            })
        cursor = page.get("meta", {}).get("next_cursor")
        if not cursor:
            break
        params["cursor"] = cursor
        time.sleep(0.2)
    return works

def _root_openalex():
    return ref("openalex")  # <- sempre aqui

def _save_bundle(author: Dict[str, Any], works: List[Dict[str, Any]]) -> Tuple[str, str]:
    author_id = (author.get("id") or "").split("/")[-1]
    if not author_id:
        raise RuntimeError("Author sem ID")
    ts = str(int(time.time()))
    summary = {
        "author_id": author_id,
        "display_name": author.get("display_name"),
        "orcid": (author.get("orcid") or "").split("/")[-1] if author.get("orcid") else None,
        "works_count": author.get("works_count"),
        "cited_by_count": author.get("cited_by_count"),
        "last_import_ts": int(ts),
    }
    bundle = {
        "author": author,
        "works": { (w["workId"] or f"auto_{i}"): w for i, w in enumerate(works) },
        "imported_at": int(ts),
    }
    root = _root_openalex().child(author_id)
    root.child("summary").update(summary)
    root.child("batches").child(ts).set(bundle)
    return author_id, ts

@router.post("/orcid", summary="Ingest por ORCID")
def ingest_orcid(orcid_list: List[str] = Body(embed=True, default=[])):
    try:
        if not orcid_list:
            raise HTTPException(400, "Envie orcid_list no body.")
        results = []
        for orcid in orcid_list:
            author = get_author_by_orcid(orcid)
            if not author:
                results.append({"orcid": orcid, "status": "NOT_FOUND"})
                continue
            works_url = author.get("works_api_url")
            works = list_works_for_author(works_url) if works_url else []
            author_id, batch_id = _save_bundle(author, works)
            results.append({"orcid": orcid, "author_id": author_id, "batchId": batch_id, "works": len(works)})
        return {"ingested": results}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Falha no ingest por ORCID: {e}")
