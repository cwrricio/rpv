# functions/http/processamento_openalex.py
from fastapi import APIRouter, HTTPException
from typing import Any, Dict

router = APIRouter(tags=["Processamento OpenAlex"])  # prefix no main.py

def _db():
    from config.firebase_admin_init import init_firebase
    from firebase_admin import db
    init_firebase()
    return db

@router.post("/{author_id}", summary="Processar último batch de /openalex/{author_id}")
def process(author_id: str) -> Dict[str, Any]:
    db = _db()
    root = db.reference("openalex").child(author_id)
    batches = root.child("batches").get() or {}
    if not batches:
        raise HTTPException(404, "Nenhum batch para esse author_id")
    last_ts = sorted(batches.keys())[-1]
    batch = batches[last_ts]
    # TODO: sua lógica de processamento aqui...
    root.child("summary").update({"last_processed_ts": int(last_ts)})
    return {"author_id": author_id, "processed_batch": last_ts, "works": len(batch.get("works", {}))}
