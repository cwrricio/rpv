# functions/ingest/openalex_name.py
from fastapi import APIRouter, HTTPException, Body, Query
from typing import Dict, Any, List, Optional, Tuple
import time, requests, traceback
from urllib.parse import urlparse
from config.settings import settings
from functions.common.dbref import ref

router = APIRouter(tags=["OpenAlex Name"])  # prefix fica no main.py
OPENALEX_BASE = "https://api.openalex.org"

# =========================
# Helpers de normalização
# =========================
def _id_tail(v: Optional[str]) -> Optional[str]:
    if not v:
        return None
    v = v.strip()
    return v.split("/")[-1] if "/" in v else v

def _normalize_author_id(author_id_or_url: str) -> str:
    """
    Aceita: "A123...", "https://openalex.org/A123...",
            "https://api.openalex.org/authors/A123..."
    Retorna sempre: "A123..."
    """
    s = (author_id_or_url or "").strip()
    if not s:
        return s
    if s.startswith("http"):
        # "/A123..." ou "/authors/A123..."
        path = urlparse(s).path
        parts = [p for p in path.split("/") if p]
        return parts[-1] if parts else s
    return s  # já é "A123..."

# =========================
# HTTP helpers (API OpenAlex)
# =========================
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

    r = requests.get(
        url,
        params=params,
        headers=_ua_headers(),
        timeout=timeout,
        allow_redirects=False,  # não seguir redirect (site HTML)
    )

    if r.is_redirect or r.is_permanent_redirect:
        loc = r.headers.get("Location", "")
        raise HTTPException(502, f"OpenAlex redirect {r.status_code} → {loc}")

    if not (200 <= r.status_code < 300):
        raise HTTPException(502, f"OpenAlex {r.status_code}: {r.text[:300].replace('\\n', ' ')}")

    ctype = (r.headers.get("Content-Type") or "").lower()
    if "json" not in ctype:
        raise HTTPException(502, f"OpenAlex content-type '{ctype}' em {r.url}: {r.text[:300].replace('\\n', ' ')}")

    try:
        return r.json()
    except Exception as e:
        raise HTTPException(502, f"Falha ao decodificar JSON: {e}")

# =========================
# Funções OpenAlex (API)
# =========================
def search_authors_by_name(name: str, per_page: int = 10) -> Dict[str, Any]:
    return http_get(f"{OPENALEX_BASE}/authors", params={"search": name, "per_page": per_page})

def fetch_author(author_id_or_url: str) -> Dict[str, Any]:
    """
    Aceita: "A123..." ou URL; sempre chama /authors/{A...} na API.
    """
    aid = _normalize_author_id(author_id_or_url)
    if not aid:
        raise HTTPException(400, "author_id inválido")
    url = f"{OPENALEX_BASE}/authors/{aid}"
    return http_get(url)

def list_works_for_author(works_url_or_author_id: str, max_pages: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Aceita 'works_api_url' OU um 'A123...'.
    Se for ID, monta: /works?filter=author.id:A123
    """
    if works_url_or_author_id.startswith("http"):
        url = works_url_or_author_id
    else:
        aid = _normalize_author_id(works_url_or_author_id)
        if not aid:
            raise HTTPException(400, "author_id inválido para listar works")
        url = f"{OPENALEX_BASE}/works?filter=author.id:{aid}"

    works: List[Dict[str, Any]] = []
    params = {"per_page": 200, "cursor": "*"}
    pages = 0
    while True:
        page = http_get(url, params=params)
        for w in page.get("results", []):
            hv = w.get("host_venue") or {}
            works.append({
                "workId": (w.get("id") or "").split("/")[-1] or None,
                "title": w.get("display_name"),
                "type": w.get("type") or None,
                "year": w.get("publication_year"),
                "doi": w.get("doi"),
                "url": None,  # resolvido depois pelo normalizador (se você usar)
                "venue": hv.get("display_name"),
                "open_access": (w.get("open_access") or {}),
                "cited_by_count": w.get("cited_by_count"),
                "concepts": w.get("concepts"),
                "authorships": w.get("authorships"),
                "primary_location": w.get("primary_location"),
            })
        pages += 1
        next_cursor = page.get("meta", {}).get("next_cursor")
        if not next_cursor or (max_pages and pages >= max_pages):
            break
        params["cursor"] = next_cursor
        time.sleep(0.2)
    return works

# =========================
def _root_openalex():
    return ref("openalex")  # <- sempre salva aqui

def _save_bundle(author: Dict[str, Any], works: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Salva em:
      /openalex/{author_id}/summary
      /openalex/{author_id}/batches/{ts}/(author,works)
    """
    author_id = (author.get("id") or "").split("/")[-1]
    if not author_id:
        raise RuntimeError("Author sem ID")

    ts = str(int(time.time()))
    summary = {
        "author_id": author_id,
        "display_name": author.get("display_name"),
        "orcid": _id_tail(author.get("orcid")),
        "works_count": author.get("works_count"),
        "cited_by_count": author.get("cited_by_count"),
        "last_import_ts": int(ts),
    }
    bundle = {
        "author": author,
        "works": { (w.get("workId") or f"auto_{i}"): w for i, w in enumerate(works) },
        "imported_at": int(ts),
    }

    root = _root_openalex().child(author_id)
    root.child("summary").update(summary)
    root.child("batches").child(ts).set(bundle)
    return author_id, ts

# =========================
# Seleção do melhor autor
# =========================
def _pick_best_author(results: List[Dict[str, Any]], prefer_orcid: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if not results:
        return None
    if prefer_orcid:
        prefer_orcid = _id_tail(prefer_orcid)
        for a in results:
            a_orcid = _id_tail(a.get("orcid"))
            if a_orcid == prefer_orcid:
                return a
    ranked = sorted(results, key=lambda a: (a.get("cited_by_count") or 0, a.get("works_count") or 0), reverse=True)
    return ranked[0]

# =========================
# Endpoints
# =========================
@router.get("/author_by_name", summary="Buscar autor por nome")
def author_by_name(q: str = Query(...)):
    data = search_authors_by_name(q, per_page=10)
    return {"count": data.get("meta", {}).get("count"), "results": data.get("results", [])}

@router.get("/_debug_ping", summary="Ping OpenAlex (debug)")
def _debug_ping(q: str = "alice"):
    data = http_get(f"{OPENALEX_BASE}/authors", params={"search": q, "per_page": 1})
    return {"ok": True, "meta": data.get("meta", {}), "sample": (data.get("results") or [None])[0]}

@router.post("/import_by_name", summary="Importar autor (e obras) e salvar em /openalex")
def import_by_name(
    body: Dict[str, Any] = Body(..., example={"name":"Alice","prefer_orcid":"0000-0002-1825-0097","max_pages":10})
):
    try:
        name = (body.get("name") or "").strip()
        prefer_orcid = (body.get("prefer_orcid") or "").strip() or None
        max_pages = body.get("max_pages")
        if not name:
            raise HTTPException(400, "Campo 'name' é obrigatório")

        found = search_authors_by_name(name, per_page=15)
        best = _pick_best_author(found.get("results", []), prefer_orcid=prefer_orcid)
        if not best:
            raise HTTPException(404, f"Nenhum autor encontrado para: {name}")

        full = fetch_author(best["id"])  # sempre API
        works_url = full.get("works_api_url") or f"{OPENALEX_BASE}/works?filter=author.id:{_id_tail(full.get('id'))}"
        works = list_works_for_author(works_url, max_pages=max_pages)

        author_id, batch_id = _save_bundle(full, works)
        return {
            "author_id": author_id,
            "display_name": full.get("display_name"),
            "orcid": _id_tail(full.get("orcid")),
            "works_saved": len(works),
            "batch_id": batch_id,
            "rt_db_path": f"/openalex/{author_id}/batches/{batch_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Falha ao importar por nome: {e}")

@router.post("/import_by_author_id", summary="Importar por author_id do OpenAlex (determinístico)")
def import_by_author_id(
    body: Dict[str, Any] = Body(..., example={"author_id":"A1969205036","max_pages":10})
):
    try:
        author_id_or_url = (body.get("author_id") or "").strip()
        max_pages = body.get("max_pages")
        if not author_id_or_url:
            raise HTTPException(400, "Campo 'author_id' é obrigatório (ex.: A1969205036).")

        full = fetch_author(author_id_or_url)  # aceita id ou URL completa
        works_url = full.get("works_api_url") or f"{OPENALEX_BASE}/works?filter=author.id:{_id_tail(full.get('id'))}"
        works = list_works_for_author(works_url, max_pages=max_pages)

        author_id, batch_id = _save_bundle(full, works)
        return {
            "author_id": author_id,
            "display_name": full.get("display_name"),
            "orcid": _id_tail(full.get("orcid")),
            "works_saved": len(works),
            "batch_id": batch_id,
            "rt_db_path": f"/openalex/{author_id}/batches/{batch_id}"
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Falha ao importar por author_id: {e}")

@router.post(
    "/import_batch_by_names",
    summary="Importar vários autores por nome (salva em /openalex e opcionalmente em /autores)"
)
def import_batch_by_names(
    body: Dict[str, Any] = Body(
        ...,
        example={
            "names": ["Silvio Quincozes", "Gilleanes Guedes"],
            "prefer_orcid_map": {"Gilleanes Guedes": "0000-0001-5457-2600"},
            "max_pages": 5,
            "also_generate_autores": True
        }
    )
):
    """
    Campos:
      - names: lista de nomes a buscar no OpenAlex
      - prefer_orcid_map: dict opcional { "Nome Exato": "0000-000X-..." } para resolver homônimos
      - max_pages: limitar paginação de works (200 por página)
      - also_generate_autores: se True, faz upsert em /autores, deduplicando por ORCID
    """
    try:
        names: List[str] = body.get("names") or []
        prefer_orcid_map: Dict[str, str] = body.get("prefer_orcid_map") or {}
        max_pages = body.get("max_pages")
        also_generate = bool(body.get("also_generate_autores"))

        if not names:
            raise HTTPException(400, "Envie 'names': [\"Nome 1\", \"Nome 2\", ...]")

        # --- helpers locais para /autores ---
        def _ref(path: str):
            return ref(path)

        def _first_last_known_institution(author_obj: Dict[str, Any]) -> Dict[str, Any] | None:
            lki = author_obj.get("last_known_institutions") or []
            return lki[0] if isinstance(lki, list) and lki else None

        def _upsert_autor_from_openalex(author_obj: Dict[str, Any]) -> str:
            """
            Usa ORCID como chave de deduplicação.
            Se tiver ORCID, atualiza; senão cria novo.
            Retorna autor_id em /autores.
            """
            autores_ref = _ref("autores")
            orcid_tail = _id_tail(author_obj.get("orcid"))
            lki = _first_last_known_institution(author_obj) or {}
            payload = {
                "nome": author_obj.get("display_name"),
                "orcid": orcid_tail,
                "openalex_author_id": _id_tail(author_obj.get("id")),
                "metrics": {
                    "works_count": author_obj.get("works_count"),
                    "cited_by_count": author_obj.get("cited_by_count"),
                },
                "instituicao": lki.get("display_name"),
                "country_code": lki.get("country_code"),
                "updated_at": int(time.time()),
            }
            if orcid_tail:
                existing = autores_ref.get() or {}
                if isinstance(existing, dict):
                    for k, v in existing.items():
                        if isinstance(v, dict) and _id_tail(v.get("orcid")) == orcid_tail:
                            autores_ref.child(k).update(payload)
                            return k
            new_id = autores_ref.push().key
            autores_ref.child(new_id).set(payload)
            return new_id

        results = []
        for name in names:
            name_s = (name or "").strip()
            if not name_s:
                results.append({"name": name, "status": "SKIPPED_EMPTY"})
                continue

            try:
                found = search_authors_by_name(name_s, per_page=15)
                best = _pick_best_author(found.get("results", []), prefer_orcid=prefer_orcid_map.get(name_s))
                if not best:
                    results.append({"name": name_s, "status": "NOT_FOUND"})
                    continue

                full = fetch_author(best["id"])
                works_url = full.get("works_api_url") or f"{OPENALEX_BASE}/works?filter=author.id:{_id_tail(full.get('id'))}"
                works = list_works_for_author(works_url, max_pages=max_pages)
                author_id, batch_id = _save_bundle(full, works)

                autor_id = None
                if also_generate:
                    try:
                        autor_id = _upsert_autor_from_openalex(full)
                    except Exception:
                        autor_id = None  # não falha o lote por causa de /autores

                results.append({
                    "name": name_s,
                    "status": "IMPORTED",
                    "author_id": author_id,
                    "display_name": full.get("display_name"),
                    "orcid": _id_tail(full.get("orcid")),
                    "works_saved": len(works),
                    "batch_id": batch_id,
                    "rt_db_path": f"/openalex/{author_id}/batches/{batch_id}",
                    "autor_id": autor_id
                })
            except HTTPException as he:
                results.append({"name": name_s, "status": f"ERROR_{he.status_code}", "detail": he.detail})
            except Exception as e:
                results.append({"name": name_s, "status": "ERROR_500", "detail": str(e)})

        return {"ok": True, "items": results}

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Falha no import_batch_by_names: {e}")
