import os, time, json, unicodedata
from typing import Dict, Any, List
import requests
from dotenv import load_dotenv

load_dotenv()

RTDB_URL = (os.getenv("RTDB_URL") or "").rstrip("/")
RTDB_AUTH = os.getenv("RTDB_AUTH")
OPENALEX_MAILTO = (os.getenv("OPENALEX_MAILTO") or "").strip()
OPENALEX_BASE = "https://api.openalex.org"

def _headers() -> Dict[str, str]:
    ua = f"poshboard/0.1 (mailto:{OPENALEX_MAILTO})" if OPENALEX_MAILTO else "poshboard/0.1"
    return {"User-Agent": ua, "From": OPENALEX_MAILTO, "Accept": "application/json"}

def _ok_json(r: requests.Response) -> Any:
    if not (200 <= r.status_code < 300):
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300].replace('\\n',' ')}")
    if "json" not in (r.headers.get("Content-Type") or "").lower():
        raise RuntimeError(f"Content-Type inesperado: {r.headers.get('Content-Type')}")
    return r.json()

def _slugify(name: str) -> str:
    s = unicodedata.normalize("NFD", name)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = s.lower().strip().replace("&", " e ")
    allowed = "abcdefghijklmnopqrstuvwxyz0123456789_ "
    s = "".join(ch if ch in allowed else "_" for ch in s)
    return "_".join(s.split()).strip("_")

# -------- OpenAlex --------

def find_author_by_orcid(orcid: str) -> Dict[str, Any]:
    """Procura via filter=orcid:. Retorna o objeto 'results[0]' ou lança erro se não achar."""
    tail = orcid.strip().split("/")[-1]
    params = {"filter": f"orcid:{tail}", "per_page": 1}
    if OPENALEX_MAILTO:
        params["mailto"] = OPENALEX_MAILTO
    r = requests.get(f"{OPENALEX_BASE}/authors", params=params, headers=_headers(), timeout=30)
    data = _ok_json(r)
    results = data.get("results") or []
    if not results:
        raise RuntimeError(f"ORCID {tail} não encontrado no OpenAlex (count=0).")
    return results[0]

def fetch_author_full(author_id_or_url: str) -> Dict[str, Any]:
    aid = author_id_or_url.split("/")[-1]
    params = {"mailto": OPENALEX_MAILTO} if OPENALEX_MAILTO else {}
    r = requests.get(f"{OPENALEX_BASE}/authors/{aid}", params=params, headers=_headers(), timeout=30)
    return _ok_json(r)

def fetch_author_works(works_api_url: str, max_pages: int = 1) -> List[Dict[str, Any]]:
    if not works_api_url: return []
    params = {"per_page": 200, "cursor": "*"}
    if OPENALEX_MAILTO: params["mailto"] = OPENALEX_MAILTO
    out, pages = [], 0
    while True:
        r = requests.get(works_api_url, params=params, headers=_headers(), timeout=40)
        data = _ok_json(r)
        for w in data.get("results", []):
            out.append({
                "id": (w.get("id") or "").split("/")[-1],
                "title": w.get("display_name"),
                "year": w.get("publication_year"),
                "doi": w.get("doi"),
                "type": w.get("type"),
                "host_venue": (w.get("host_venue") or {}).get("display_name"),
                "cited_by_count": w.get("cited_by_count"),
            })
        pages += 1
        nc = data.get("meta", {}).get("next_cursor")
        if not nc or pages >= max_pages: break
        params["cursor"] = nc
        time.sleep(0.2)
    return out

def flatten_author(a: Dict[str, Any], works: List[Dict[str, Any]]) -> (str, Dict[str, Any]):
    display_name = a.get("display_name") or ""
    slug = _slugify(display_name or a.get("id", "autor"))

    data = {
        "nome": display_name,
        "ids": {
            "openalex_author_id": (a.get("id") or "").split("/")[-1],
            "orcid": (a.get("orcid") or "").split("/")[-1] if a.get("orcid") else None,
        },
        "profile": {
            "display_name": display_name,
            "display_name_alternatives": a.get("display_name_alternatives") or [],
            "created_date": a.get("created_date"),
            "updated_date": a.get("updated_date"),
            "last_known_institutions": [
                (inst or {}).get("display_name")
                for inst in (a.get("last_known_institutions") or [])
            ],
        },
        "affiliations": [
            {
                "name": ((aff.get("institution") or {}).get("display_name")),
                "country_code": ((aff.get("institution") or {}).get("country_code")),
                "years": aff.get("years"),
            }
            for aff in (a.get("affiliations") or [])
        ],
        "topics": [t.get("display_name") for t in (a.get("topics") or [])],
        "metrics": {
            "works_count": a.get("works_count"),
            "cited_by_count": a.get("cited_by_count"),
            "h_index": (a.get("summary_stats") or {}).get("h_index"),
            "i10_index": (a.get("summary_stats") or {}).get("i10_index"),
        },
        "works": works,
        "updated_at": int(time.time()),
    }
    return slug, data

# -------- Firebase RTDB --------

def rtdb_put(path: str, data: Any) -> Any:
    if not RTDB_URL: raise RuntimeError("Defina RTDB_URL no .env")
    url = f"{RTDB_URL}/{path}.json"
    if RTDB_AUTH: url += f"?auth={RTDB_AUTH}"
    r = requests.put(url, data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
                     headers={"Content-Type": "application/json"}, timeout=30)
    return _ok_json(r)

def save_to_autores_flat(slug: str, data: Dict[str, Any]):
    return rtdb_put(f"autores_flat/{slug}", data)

# -------- Pipeline --------

def ingest_orcid_to_autores_flat(orcid: str, max_pages_works: int = 1):
    try:
        hit = find_author_by_orcid(orcid)          # 1) procura via filter
        full = fetch_author_full(hit["id"])        # 2) baixa autor completo
        works = fetch_author_works(full.get("works_api_url"), max_pages=max_pages_works)
        slug, flat = flatten_author(full, works)   # 3) achata
        save_to_autores_flat(slug, flat)           # 4) salva
        print(f"[OK] {orcid} → autores_flat/{slug} (works={len(works)})")
    except Exception as e:
        print(f"[ERRO] {orcid}: {e}")

if __name__ == "__main__":
    orcids = [
        "0000-0002-5420-6966",
    ]
    for oc in orcids:
        ingest_orcid_to_autores_flat(oc, max_pages_works=1)
