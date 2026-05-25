# functions/api_routes/processamento_openalex.py
from fastapi import APIRouter, HTTPException
from typing import Any, Dict
from functions.common.dbref import ref

router = APIRouter(tags=["Processamento OpenAlex"])  # prefix no main.py

@router.post("/{author_id}", summary="Processar último batch de /openalex/{author_id}")
def process(author_id: str) -> Dict[str, Any]:
    root = ref("openalex").child(author_id)
    batches = root.child("batches").get() or {}
    if not batches:
        raise HTTPException(404, "Nenhum batch para esse author_id")
    last_ts = sorted(batches.keys())[-1]
    batch = batches[last_ts]
    # TODO: sua lógica de processamento aqui...
    root.child("summary").update({"last_processed_ts": int(last_ts)})
    return {"author_id": author_id, "processed_batch": last_ts, "works": len(batch.get("works", {}))}
