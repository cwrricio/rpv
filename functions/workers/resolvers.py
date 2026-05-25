# functions/workers/resolvers.py
def _ext():  # /external_ids
    from config.firebase_admin_init import init_firebase
    from firebase_admin import db
    init_firebase()
    return db.reference("external_ids")

def _veiculos():
    from config.firebase_admin_init import init_firebase
    from firebase_admin import db
    init_firebase()
    return db.reference("veiculos")

def _docentes():
    from config.firebase_admin_init import init_firebase
    from firebase_admin import db
    init_firebase()
    return db.reference("docentes")

def _externos():
    from config.firebase_admin_init import init_firebase
    from firebase_admin import db
    init_firebase()
    return db.reference("externos")

def slug_doi(doi: str) -> str:
    return (doi or "").lower().strip().replace("/", "_")

def resolve_produto_by_doi(doi: str) -> str | None:
    if not doi:
        return None
    s = _ext().child("doi").child(slug_doi(doi)).get()
    return s.get("prodId") if isinstance(s, dict) else None

def link_doi_to_produto(doi: str, prod_id: str):
    if doi:
        _ext().child("doi").child(slug_doi(doi)).set({"prodId": prod_id})

def resolve_or_upsert_veiculo(issn: str, nome: str | None = None) -> str:
    issn = (issn or "").strip()
    if not issn:
        ref = _veiculos().push({"nome": nome or "Desconhecido"})
        return ref.key
    link = _ext().child("issn").child(issn).get()
    if link and isinstance(link, dict) and link.get("veicId"):
        return link["veicId"]
    vref = _veiculos().push({"nome": nome or "Desconhecido", "issn": issn})
    _ext().child("issn").child(issn).set({"veicId": vref.key})
    return vref.key

def resolve_pessoa_by_orcid(orcid: str) -> tuple[str, str] | None:
    if not orcid:
        return None
    q = _docentes().order_by_child("orcid").equal_to(orcid).get() or {}
    for doc_id, d in q.items():
        if isinstance(d, dict) and d.get("orcid") == orcid:
            return ("docente", doc_id)
    q2 = _externos().order_by_child("orcid").equal_to(orcid).get() or {}
    for ext_id, e in q2.items():
        if isinstance(e, dict) and e.get("orcid") == orcid:
            return ("externo", ext_id)
    ext_ref = _externos().push({"nome": None, "email": None, "afiliacao": None, "orcid": orcid})
    return ("externo", ext_ref.key)
