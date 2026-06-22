from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
import time
from functions.common.dbref import ref
from functions.common import http_client

router = APIRouter(prefix="/ingest/semanticscholar", tags=["Semantic Scholar"])

BASE = "https://api.semanticscholar.org/graph/v1"

def _ref(p: str):
    return ref(p)

def _headers():
    # sem chave é ok (rate limit baixo). Pode setar um User-Agent custom se quiser.
    return {"Accept": "application/json", "User-Agent": "poshboard/0.1"}

def s2_author_search(q: str, limit: int = 5) -> Dict[str, Any]:
    try:
        return http_client.get(
            f"{BASE}/author/search",
            params={"query": q, "limit": limit, "fields": "name,affiliations,homepage,paperCount,citationCount,hIndex"},
            headers=_headers(),
            timeout=25,
        )
    except Exception as exc:
        raise HTTPException(502, f"S2 error: {exc}") from exc

def s2_author(author_id: str, with_papers: bool = True, papers_limit: int = 200) -> Dict[str, Any]:
    fields = "name,aliases,affiliations,homepage,photoUrl,externalIds,paperCount,citationCount,hIndex"
    if with_papers:
        fields += ",papers.title,papers.year,papers.citationCount,papers.externalIds,papers.venue,papers.authors"
    try:
        return http_client.get(
            f"{BASE}/author/{author_id}",
            params={"fields": fields, "limit": papers_limit},
            headers=_headers(),
            timeout=25,
        )
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status == 404:
            raise HTTPException(404, f"S2 autor {author_id} não encontrado") from exc
        raise HTTPException(502, f"S2 error: {exc}") from exc

@router.get("/author_search", summary="Procurar autor por nome (S2)")
def author_search(q: str = Query(...), limit: int = Query(5)):
    return s2_author_search(q, limit=limit)

@router.post("/import_author", summary="Baixar perfil e papers (S2) e salvar em /external/semanticscholar/{id}")
def import_author(body: Dict[str, Any] = Body(..., example={"author_id": "144672504", "with_papers": True, "papers_limit": 200})):
    author_id = (body.get("author_id") or "").strip()
    with_papers = bool(body.get("with_papers", True))
    papers_limit = int(body.get("papers_limit", 200))
    if not author_id:
        raise HTTPException(400, "author_id é obrigatório")
    data = s2_author(author_id, with_papers=with_papers, papers_limit=papers_limit)
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
    return {"ok": True, "author_id": author_id, "saved_to": f"/external/semanticscholar/{author_id}"}
