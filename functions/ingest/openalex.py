# functions/ingest/openalex.py
from fastapi import APIRouter, HTTPException, Query
import time, hashlib, json
from functions.common.dbref import ref
from functions.common import http_client
from functions.common import metadata_cache

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
    sleep_ms: int = 400,
    use_cache: bool = Query(default=True, description="Usar cache local quando disponível")
):
    if per_page < 1 or per_page > 200:
        raise HTTPException(400, "per_page deve estar entre 1 e 200")

    params = {"per_page": per_page}
    if search: params["search"] = search
    if filter: params["filter"] = filter

    batch_id = f"openalex_{int(time.time())}"
    items_ref = _staging_ref().child(batch_id).child("items")

    total = 0
    from_cache = 0
    cursor = "*"
    for _ in range(max_pages):
        ps = {**params, "cursor": cursor}
        try:
            # Tentar cache primeiro se use_cache=True
            if use_cache:
                # Cache por parâmetros de busca
                cache_key = f"search:{hashlib.sha256(json.dumps(ps, sort_keys=True).encode()).hexdigest()}"
                cached = metadata_cache.get_cached("OPENALEX", cache_key, "obra", max_age=300)  # 5 min para buscas
                if cached:
                    data = cached
                    from_cache += len(data.get("results", []))
                else:
                    data = http_client.get(OPENALEX_BASE, params=ps, timeout=30, cache_ttl=0)
                    # Cache do resultado da busca
                    metadata_cache.set_cache("OPENALEX", cache_key, "obra", data)
            else:
                data = http_client.get(OPENALEX_BASE, params=ps, timeout=30, cache_ttl=0)
        except Exception as exc:
            # Fallback: tentar buscar do cache mesmo expirado
            if use_cache:
                logger = logging.getLogger(__name__)
                logger.warning("Falha na API, tentando cache expirado: %s", exc)
                cached = metadata_cache.get_cached("OPENALEX", cache_key, "obra", max_age=86400*30)
                if cached:
                    data = cached
                    from_cache += len(data.get("results", []))
                else:
                    raise HTTPException(502, f"OpenAlex error: {exc}") from exc
            else:
                raise HTTPException(502, f"OpenAlex error: {exc}") from exc

        for work in data.get("results", []):
            h = _hash_payload(work)
            items_ref.child(h[:16]).set({
                "source": "OPENALEX",
                "hash": h,
                "raw": work,
                "createdAt": time.time(),
                "from_cache": from_cache > 0
            })
            total += 1

        cursor = (data.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
        time.sleep(max(sleep_ms, 0) / 1000.0)

    _prov_ref().child(batch_id).set({
        "source": "OPENALEX",
        "count": total,
        "from_cache": from_cache,
        "params": params,
        "createdAt": time.time()
    })
    return {"batchId": batch_id, "items": total, "from_cache": from_cache}
