# functions/ingest/openalex.py
from fastapi import APIRouter, HTTPException, Query
import requests, time, hashlib, json
from functions.common.dbref import ref

router = APIRouter(prefix="/ingest/openalex", tags=["Ingestão OpenAlex"])
OPENALEX_BASE = "https://api.openalex.org/works"

def _hash_payload(d: dict) -> str:
    import hashlib, json
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()

def _staging_ref():
    return ref("staging/import_batches")

def _prov_ref():
    return ref("provenance")

@router.post("/works")
def ingest_works(
    search: str | None = Query(default=None, description="ex: machine learning"),
    filter: str | None = Query(default=None, description="ex: from_publication_date:2024-01-01,type:journal-article"),
    per_page: int = 50,
    max_pages: int = 2,
    sleep_ms: int = 400
):
    if per_page < 1 or per_page > 200:
        raise HTTPException(400, "per_page deve estar entre 1 e 200")

    params = {"per_page": per_page}
    if search: params["search"] = search
    if filter: params["filter"] = filter

    batch_id = f"openalex_{int(time.time())}"
    items_ref = _staging_ref().child(batch_id).child("items")

    total = 0
    cursor = "*"
    for _ in range(max_pages):
        ps = {**params, "cursor": cursor}
        r = requests.get(OPENALEX_BASE, params=ps, timeout=30)
        if r.status_code != 200:
            raise HTTPException(r.status_code, f"OpenAlex error: {r.text}")
        data = r.json()

        for work in data.get("results", []):
            h = _hash_payload(work)
            items_ref.child(h[:16]).set({
                "source": "OPENALEX",
                "hash": h,
                "raw": work,
                "createdAt": time.time()
            })
            total += 1

        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(max(sleep_ms, 0) / 1000.0)

    _prov_ref().child(batch_id).set({
        "source": "OPENALEX",
        "count": total,
        "params": params,
        "createdAt": time.time()
    })
    return {"batchId": batch_id, "items": total}
