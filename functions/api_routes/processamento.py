# functions/http/processamento.py
from fastapi import APIRouter, HTTPException
from functions.workers.batch_processor import process_batch

router = APIRouter(prefix="/process", tags=["Processamento"])

@router.post("/batch/{batch_id}")
def run_batch(batch_id: str):
    try:
        result = process_batch(batch_id)
        return {"batchId": batch_id, **result}
    except Exception as e:
        raise HTTPException(500, str(e))
