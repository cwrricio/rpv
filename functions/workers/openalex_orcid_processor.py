# functions/workers/openalex_orcid_processor.py
from typing import Dict, Any, Optional
import time

from functions.workers.openalex_mapper import subtype_from_openalex_type
from functions.workers.upsert import upsert_produto_bibliografico
from functions.common.dbref import ref

def _staging_orcid(orcid: str):
    return ref("staging/orcid_bundles").child(orcid)

def _latest_batch_id(orcid: str) -> Optional[str]:
    batches = _staging_orcid(orcid).child("batches").get() or {}
    if not isinstance(batches, dict) or not batches:
        return None
    # pega o maior timestamp
    return sorted(batches.keys())[-1]

def _map_work_to_prod_from_orcid_bundle(work: Dict[str, Any]) -> Dict[str, Any]:
    # converte a estrutura “works” (do ingest_orcid) para o formato do upsert
    issn = None   # openalex "works" mapeado acima não trouxe issn; opcional buscar no /works/{id}
    veiculo_nome = work.get("venue")

    autores = []
    auths = work.get("authorships") or []
    for i, a in enumerate(auths, start=1):
        # aqui só sabemos ORCID se você enriquecer antes; OpenAlex author struct nem sempre tem ORCID
        # vamos carregar como “externo_orcid=None” e tratar em outra passada, se necessário
        autores.append({
            "papel": "AUTOR",
            "posicao": i,
            "contribuicao": None,
            "externo_orcid": None
        })

    return {
        "tipo": "BIBLIOGRAFICA",
        "subtipo": subtype_from_openalex_type(work.get("type")),
        "titulo": work.get("title"),
        "ano": work.get("year"),
        "url": work.get("url"),
        "doi": work.get("doi"),
        "issn": issn,
        "veiculo_nome": veiculo_nome,
        "autores": autores
    }

def process_orcid(orcid: str, batch_id: Optional[str] = None) -> Dict[str, Any]:
    if not batch_id:
        batch_id = _latest_batch_id(orcid)
    if not batch_id:
        return {"orcid": orcid, "processed": 0, "errors": 0, "note": "no batch"}

    bundle = _staging_orcid(orcid).child("batches").child(batch_id).get() or {}
    works = bundle.get("works") or {}

    processed, errors = 0, 0
    for _, w in works.items():
        try:
            mapped = _map_work_to_prod_from_orcid_bundle(w)
            upsert_produto_bibliografico(mapped)
            processed += 1
        except Exception:
            errors += 1

    _staging_orcid(orcid).child("batches").child(batch_id).update({
        "processedAt": int(time.time()),
        "processed": processed,
        "errors": errors
    })

    return {"orcid": orcid, "batchId": batch_id, "processed": processed, "errors": errors}
