# functions/workers/upsert.py
from .resolvers import (
    resolve_or_upsert_veiculo,
    resolve_produto_by_doi,
    link_doi_to_produto,
    resolve_pessoa_by_orcid,
)

def _produtos():
    from config.firebase_admin_init import init_firebase
    from firebase_admin import db
    init_firebase()
    return db.reference("produtos")

def _autores():
    from config.firebase_admin_init import init_firebase
    from firebase_admin import db
    init_firebase()
    return db.reference("autores")

def upsert_produto_bibliografico(m: dict) -> str:
    prod_id = None
    if m.get("doi"):
        prod_id = resolve_produto_by_doi(m["doi"])

    if not prod_id:
        prod_ref = _produtos().push({
            "tipo": "BIBLIOGRAFICA",
            "subtipo": m.get("subtipo"),
            "titulo": m.get("titulo"),
            "ano": m.get("ano"),
            "url": m.get("url"),
        })
        prod_id = prod_ref.key
        if m.get("doi"):
            link_doi_to_produto(m["doi"], prod_id)
    else:
        _produtos().child(prod_id).update({
            "subtipo": m.get("subtipo"),
            "titulo": m.get("titulo"),
            "ano": m.get("ano"),
            "url": m.get("url"),
        })

    if m.get("issn") or m.get("veiculo_nome"):
        veic_id = resolve_or_upsert_veiculo(m.get("issn"), m.get("veiculo_nome"))
        _produtos().child(prod_id).update({"veiculo_id": veic_id})

    if isinstance(m.get("autores"), list):
        prev = _autores().order_by_child("produto_id").equal_to(prod_id).get() or {}
        for key in list(prev.keys()):
            _autores().child(key).delete()

        for a in m["autores"]:
            payload = {
                "produto_id": prod_id,
                "papel": a.get("papel", "AUTOR"),
                "posicao": a.get("posicao"),
                "contribuicao": a.get("contribuicao"),
                "docente_id": None,
                "discente_id": None,
                "externo_id": None,
            }
            ext_orcid = a.get("externo_orcid")
            if ext_orcid:
                found = resolve_pessoa_by_orcid(ext_orcid)
                if found:
                    tipo, pid = found
                    if tipo == "docente":
                        payload["docente_id"] = pid
                    else:
                        payload["externo_id"] = pid
            _autores().push(payload)

    return prod_id
