from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional, List
import time
from functions.common.dbref import ref

router = APIRouter(prefix="/autores", tags=["Autores • Merge"])

def _ref(p: str):
    return ref(p)

def _tail_orcid(v: Optional[str]) -> Optional[str]:
    if not v: return None
    v = v.strip()
    return v.split("/")[-1] if "/" in v else v

def _find_autor_by_orcid_tail(tail: Optional[str]) -> Optional[str]:
    if not tail: return None
    raw = _ref("autores").get() or {}
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, dict) and _tail_orcid(v.get("orcid")) == tail:
                return k
    return None

@router.post("/merge_sources", summary="Consolidar dados de external/* em /autores (upsert por ORCID)")
def merge_sources(body: Dict[str, Any] = Body(..., example={
    "orcid": "0000-0001-5457-2600",
    "openalex_author_id": "A5065070393",
    "semanticscholar_author_id": "144672504",
    "crossref_author_name": "Gilleanes Thorwald Araujo Guedes"
})):
    orcid_tail = _tail_orcid(body.get("orcid"))
    openalex_id = (body.get("openalex_author_id") or "").strip() or None
    s2_id = (body.get("semanticscholar_author_id") or "").strip() or None
    crossref_key = (body.get("crossref_author_name") or "").strip().lower().replace("  ", " ") or None

    # coleta dados das fontes (se existirem)
    summary = {}
    if openalex_id:
        oa = _ref(f"openalex/{openalex_id}/summary").get() or {}
        if oa:
            summary["nome"] = oa.get("display_name") or summary.get("nome")
            summary["orcid"] = orcid_tail or _tail_orcid(oa.get("orcid"))
            summary.setdefault("metrics", {})
            summary["metrics"]["works_count"] = oa.get("works_count")
            summary["metrics"]["cited_by_count"] = oa.get("cited_by_count")
            summary["openalex_author_id"] = openalex_id

    if orcid_tail:
        oc = _ref(f"external/orcid/{orcid_tail}/summary").get() or {}
        if oc:
            summary["nome"] = oc.get("display_name") or summary.get("nome")
            summary["orcid"] = orcid_tail

    if s2_id:
        s2 = _ref(f"external/semanticscholar/{s2_id}/summary").get() or {}
        if s2:
            summary["nome"] = s2.get("name") or summary.get("nome")
            summary.setdefault("metrics", {})
            summary["metrics"]["hIndex"] = s2.get("hIndex")
            summary["metrics"]["paperCount"] = s2.get("paperCount")
            summary["metrics"]["citationCount"] = s2.get("citationCount")
            summary["semanticscholar_author_id"] = s2_id

    if crossref_key:
        cr = _ref(f"external/crossref/by_author_name/{crossref_key}/summary").get() or {}
        if cr:
            summary.setdefault("metrics", {})
            summary["metrics"]["crossref_works_count"] = cr.get("works_count")

    if not summary:
        raise HTTPException(400, "Nenhum dado encontrado nas fontes especificadas.")

    # upsert por ORCID (se tiver). Senão, cria novo.
    autor_id = _find_autor_by_orcid_tail(summary.get("orcid")) if summary.get("orcid") else None
    autores_ref = _ref("autores")
    if autor_id:
        autores_ref.child(autor_id).update(summary | {"updated_at": int(time.time())})
    else:
        autor_id = autores_ref.push().key
        autores_ref.child(autor_id).set(summary | {"created_at": int(time.time())})

    # guardar links de fontes
    fontes = {}
    if openalex_id: fontes["openalex_author_id"] = openalex_id
    if orcid_tail: fontes["orcid"] = orcid_tail
    if s2_id: fontes["semanticscholar_author_id"] = s2_id
    if crossref_key: fontes["crossref_name_key"] = crossref_key
    autores_ref.child(autor_id).child("sources").update(fontes)

    return {"ok": True, "autor_id": autor_id, "merged_fields": summary}
