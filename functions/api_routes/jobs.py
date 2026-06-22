from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from functions.jobs.queue import get_job_queue

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/", summary="Listar jobs recentes")
def list_jobs(
    status: Optional[str] = Query(default=None, pattern="^(queued|running|retry|succeeded|dead)$"),
    limit: int = Query(default=50, ge=1, le=200),
):
    return {"jobs": get_job_queue().list(status=status, limit=limit)}


@router.get("/{job_id}", summary="Consultar status de um job")
def get_job(job_id: str):
    job = get_job_queue().get(job_id)
    if not job:
        raise HTTPException(404, "Job nao encontrado")
    return job
