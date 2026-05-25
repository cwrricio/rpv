from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, List
import requests, time

from config.settings import settings

router = APIRouter(prefix="/ingest/crossref", tags=["Crossref"])

def _db():
    from config.firebase_admin_init import init_firebase
    from firebase_admin import db
    init_firebase()
    return db

def _ref(p: str):
    return _db().reference(p)

def _headers() -> Dict[str, str]:
    mailto = (settings.OPENALEX_MAILTO or "").strip()
    ua = f"poshboard/0.1 ({'mailto:'+mailto if mailto else 'no-mailto'})"
    h = {"User-Agent": ua, "Accept": "application/json"}
    if mailto:
        h["From"] = mailto
    return h

def crossref_works_by_author(name: str, rows: int = 100) -> Dict[str, Any]:
    url = "https://api.crossref.org/works"
    params = {"query.author": name, "rows": rows}
    r = requests.get(url, params=params, headers=_headers(), timeout=25)
    if not (200 <= r.status_code < 300):
        raise HTTPException(502, f"Crossref {r.status_code}: {r.text[:300]}")
    return r.json()

@router.post("/works_by_author_name", summary="Baixar obras no Crossref por nome de autor e salvar em /external/crossref")
def works_by_author_name(body: Dict[str, Any] = Body(..., example={"name": "Diego Luis Kreutz", "rows": 100})):
    name = (body.get("name") or "").strip()
    rows = int(body.get("rows") or 100)
    if not name:
        raise HTTPException(400, "name é obrigatório")
    data = crossref_works_by_author(name, rows=rows)
    items: List[Dict[str, Any]] = (data.get("message") or {}).get("items", [])
    ts = str(int(time.time()))
    key = name.lower().strip().replace("  ", " ").replace("/", "_")
    base = _ref(f"external/crossref/by_author_name/{key}")
    # salva lote
    base.child("batches").child(ts).set({"name": name, "items": items, "imported_at": int(ts)})
    # resumo
    dois = [it.get("DOI") for it in items if it.get("DOI")]
    base.child("summary").update({"name": name, "last_import_ts": int(ts), "works_count": len(items), "dois_sample": dois[:10]})
    return {"ok": True, "name": name, "saved_to": f"/external/crossref/by_author_name/{key}", "works": len(items)}
