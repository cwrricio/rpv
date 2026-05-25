# functions/api_routes/autores_generate.py
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List, Optional, Tuple
import unicodedata, re, time
from functions.common.dbref import ref

router = APIRouter(tags=["Autores • Gerar (OpenAlex)"])  # prefix no main.py

# ---------- Firebase helpers ----------
def _ref(path: str):
    return ref(path)

# ---------- utils ----------
def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"\s+", " ", s)
    return s

def _tail_orcid(v: Optional[str]) -> Optional[str]:
    if not v: 
        return None
    v = v.strip()
    return v.split("/")[-1] if "/" in v else v

def _load_autores_index() -> Dict[str, str]:
    """
    Retorna um índice por ORCID (tail) -> autor_id em /autores
    """
    raw = _ref("autores").get() or {}
    index: Dict[str, str] = {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, dict):
                tail = _tail_orcid(v.get("orcid"))
                if tail:
                    index[tail] = k
    return index

def _collect_openalex_author(author_id: str) -> Optional[Dict[str, Any]]:
    """
    Lê /openalex/{authorId}/summary e /openalex/{authorId}/batches (pega a última).
    Retorna um dicionário com os campos úteis para /autores.
    """
    base = _ref(f"openalex/{author_id}")
    summary = base.child("summary").get() or {}
    batches = base.child("batches").get() or {}
    if not summary and not batches:
        return None

    # tenta pegar o objeto completo do autor do último batch
    last_ts = None
    last_author_obj = None
    if isinstance(batches, dict) and batches:
        last_ts = sorted(batches.keys())[-1]
        b = batches[last_ts] or {}
        last_author_obj = (b.get("author") or {}) if isinstance(b, dict) else {}

    # preferir 'author' do batch; cair para summary se faltar
    display_name = (last_author_obj.get("display_name")
                    or summary.get("display_name"))
    orcid = (last_author_obj.get("orcid")
             or summary.get("orcid"))
    last_inst = (last_author_obj.get("last_known_institution") 
                 or summary.get("last_known_institution") 
                 or {})
    inst_name = last_inst.get("display_name")
    inst_country = last_inst.get("country_code")

    works_count = summary.get("works_count")
    cited_by_count = summary.get("cited_by_count")

    return {
        "openalex_author_id": author_id,
        "nome": display_name,
        "orcid": _tail_orcid(orcid) or None,
        "instituicao": inst_name,
        "country_code": inst_country,
        "metrics": {
            "works_count": works_count,
            "cited_by_count": cited_by_count,
            "openalex_last_sync_ts": int(time.time()),
        }
    }

def _upsert_autor_from_openalex_payload(p: Dict[str, Any], autores_idx: Dict[str, str]) -> Tuple[str, bool]:
    """
    Upsert em /autores usando ORCID (tail) como chave de deduplicação.
    Retorna (autor_id, created_flag).
    """
    autores_ref = _ref("autores")
    tail = _tail_orcid(p.get("orcid"))

    if tail and tail in autores_idx:
        autor_id = autores_idx[tail]
        autores_ref.child(autor_id).update(p)
        return autor_id, False

    # sem ORCID ou ainda não existe: cria
    new_id = autores_ref.push().key
    autores_ref.child(new_id).set(p)
    # atualiza índice em memória se tiver orcid
    if tail:
        autores_idx[tail] = new_id
    return new_id, True

# ---------- endpoints ----------
@router.post("/autores/generate_from_openalex", summary="Gerar/atualizar /autores a partir de /openalex")
def generate_from_openalex(body: Dict[str, Any] = Body(default={"author_ids": [], "all": False})):
    """
    Body:
      - author_ids: lista de IDs de autor do OpenAlex (ex.: ["A123...", "A456..."])
      - all: se True, varre todos os nós sob /openalex
    """
    author_ids: List[str] = body.get("author_ids") or []
    use_all: bool = bool(body.get("all"))

    # resolve a lista de author_ids
    if use_all:
        # varre todas as chaves em /openalex
        raw = _ref("openalex").get() or {}
        if isinstance(raw, dict):
            author_ids = list(raw.keys())

    if not author_ids:
        raise HTTPException(400, "Envie 'author_ids' ou 'all': true")

    autores_idx = _load_autores_index()
    results = {"created": [], "updated": [], "skipped": []}

    for aid in author_ids:
        payload = _collect_openalex_author(aid)
        if not payload or not (payload.get("nome") or payload.get("orcid")):
            results["skipped"].append({"openalex_author_id": aid, "reason": "not_found_or_empty"})
            continue
        autor_id, created = _upsert_autor_from_openalex_payload(payload, autores_idx)
        (results["created"] if created else results["updated"]).append({
            "openalex_author_id": aid,
            "autor_id": autor_id
        })

    return results
