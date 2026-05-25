# functions/api_routes/autores_links.py
from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List, Tuple
import unicodedata, re
from functions.common.dbref import ref

router = APIRouter(tags=["Autores ↔ Docentes"])  # prefix no main.py

# --- utilidades ---
def _norm(s: str) -> str:
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")  # remove acentos
    s = re.sub(r"\s+", " ", s)
    return s

def _only_orcid_tail(v: str | None) -> str | None:
    if not v: return None
    v = v.strip()
    return v.split("/")[-1] if "/" in v else v

# --- load data ---
def _load_docentes() -> List[Dict[str, Any]]:
    raw = ref("docentes").get() or {}
    out = []
    for k, v in (raw.items() if isinstance(raw, dict) else []):
        if not isinstance(v, dict): continue
        v = {"id": k, **v}
        v["orcid_tail"] = _only_orcid_tail(v.get("orcid"))
        v["email_norm"] = _norm(v.get("email") or "")
        v["nome_norm"] = _norm(v.get("nome") or "")
        v["instituicao_norm"] = _norm(v.get("instituicao") or v.get("affiliation") or "")
        out.append(v)
    return out

def _load_autores() -> List[Dict[str, Any]]:
    raw = ref("autores").get() or {}
    out = []
    for k, v in (raw.items() if isinstance(raw, dict) else []):
        if not isinstance(v, dict): continue
        v = {"id": k, **v}
        v["orcid_tail"] = _only_orcid_tail(v.get("orcid"))
        v["email_norm"] = _norm(v.get("email") or "")
        v["nome_norm"] = _norm(v.get("nome") or v.get("author_name") or "")
        v["instituicao_norm"] = _norm(v.get("instituicao") or v.get("affiliation") or "")
        out.append(v)
    return out

# --- matchers ---
def _match_autor_to_docente(autor: Dict[str, Any], docentes: List[Dict[str, Any]]) -> Tuple[str | None, Dict[str, Any] | None]:
    # 1) ORCID
    if autor.get("orcid_tail"):
        for d in docentes:
            if d.get("orcid_tail") and d["orcid_tail"] == autor["orcid_tail"]:
                return d["id"], {"method": "orcid", "score": 1.0}
    # 2) email
    if autor.get("email_norm"):
        for d in docentes:
            if d.get("email_norm") and d["email_norm"] == autor["email_norm"]:
                return d["id"], {"method": "email", "score": 0.95}
    # 3) nome + instituição (fraco, mas útil)
    if autor.get("nome_norm"):
        cand = [d for d in docentes if d.get("nome_norm") == autor["nome_norm"]]
        if len(cand) == 1:
            return cand[0]["id"], {"method": "name", "score": 0.8}
        if len(cand) > 1 and autor.get("instituicao_norm"):
            for d in cand:
                if d.get("instituicao_norm") and d["instituicao_norm"] == autor["instituicao_norm"]:
                    return d["id"], {"method": "name_institution", "score": 0.9}
    return None, None

# --- endpoints ---
@router.get("/autores/unlinked", summary="Listar autores sem vínculo com docente")
def list_unlinked():
    autores = _load_autores()
    return [a for a in autores if not a.get("docente_id")]

@router.post("/autores/_reconcile_all", summary="Tentar vincular todos os autores a docentes")
def reconcile_all():
    docentes = _load_docentes()
    autores = _load_autores()
    linked, skipped = [], []

    for a in autores:
        if a.get("docente_id"):
            skipped.append({"autor_id": a["id"], "reason": "already_linked"})
            continue
        docente_id, meta = _match_autor_to_docente(a, docentes)
        if docente_id:
            ref("autores").child(a["id"]).update({
                "docente_id": docente_id,
                "match": meta
            })
            linked.append({"autor_id": a["id"], "docente_id": docente_id, "match": meta})
        else:
            skipped.append({"autor_id": a["id"], "reason": "no_match"})

    return {"linked": linked, "skipped": skipped, "docentes": len(docentes), "autores": len(autores)}

@router.post("/autores/{autor_id}/link_to_docente/{docente_id}", summary="Forçar vínculo autor → docente")
def force_link(autor_id: str, docente_id: str):
    if not ref("autores").child(autor_id).get():
        raise HTTPException(404, "Autor não encontrado")
    if not ref("docentes").child(docente_id).get():
        raise HTTPException(404, "Docente não encontrado")
    ref("autores").child(autor_id).update({
        "docente_id": docente_id,
        "match": {"method": "manual", "score": 1.0}
    })
    return {"ok": True, "autor_id": autor_id, "docente_id": docente_id}
