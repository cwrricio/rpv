from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    and_,
    create_engine,
    insert,
    or_,
    select,
    update as sa_update,
)

from functions.jobs.ports import JobQueuePort

_metadata = MetaData()

job_queue = Table(
    "job_queue",
    _metadata,
    Column("id", String, primary_key=True),
    Column("task_name", String, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("status", String, nullable=False),
    Column("attempts", Integer, nullable=False, default=0),
    Column("max_attempts", Integer, nullable=False, default=3),
    Column("idempotency_key", String, unique=True, nullable=True),
    Column("created_at", Float, nullable=False),
    Column("updated_at", Float, nullable=False),
    Column("run_at", Float, nullable=False),
    Column("locked_at", Float, nullable=True),
    Column("started_at", Float, nullable=True),
    Column("finished_at", Float, nullable=True),
    Column("last_error", String, nullable=True),
    Column("result", JSON, nullable=True),
)


def _default_url() -> str:
    try:
        from config.settings import settings

        if getattr(settings, "DATABASE_URL", None):
            return settings.DATABASE_URL
    except Exception:
        pass
    return "postgresql+psycopg://poshboard:poshboard@localhost:5432/poshboard"


class SQLAlchemyJobQueue(JobQueuePort):
    def __init__(self, url: Optional[str] = None, *, retry_backoff_seconds: int = 30):
        self._engine = create_engine(url or _default_url(), future=True)
        self.retry_backoff_seconds = retry_backoff_seconds

    def init_schema(self) -> None:
        _metadata.create_all(self._engine)

    @staticmethod
    def _new_id() -> str:
        return uuid.uuid4().hex

    @staticmethod
    def _row_to_job(row: Any) -> Dict[str, Any]:
        data = dict(row._mapping if hasattr(row, "_mapping") else row)
        return data

    def enqueue(
        self,
        task_name: str,
        payload: Dict[str, Any],
        *,
        max_attempts: int = 3,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        now = time.time()
        with self._engine.begin() as conn:
            if idempotency_key:
                existing = conn.execute(
                    select(job_queue).where(job_queue.c.idempotency_key == idempotency_key)
                ).first()
                if existing is not None:
                    return self._row_to_job(existing)

            job_id = self._new_id()
            values = {
                "id": job_id,
                "task_name": task_name,
                "payload": payload,
                "status": "queued",
                "attempts": 0,
                "max_attempts": max(1, int(max_attempts)),
                "idempotency_key": idempotency_key,
                "created_at": now,
                "updated_at": now,
                "run_at": now,
                "locked_at": None,
                "started_at": None,
                "finished_at": None,
                "last_error": None,
                "result": None,
            }
            conn.execute(insert(job_queue).values(**values))
            row = conn.execute(select(job_queue).where(job_queue.c.id == job_id)).first()
        return self._row_to_job(row)

    def claim_next(self) -> Optional[Dict[str, Any]]:
        now = time.time()
        ready = and_(
            job_queue.c.status.in_(["queued", "retry"]),
            job_queue.c.run_at <= now,
        )
        with self._engine.begin() as conn:
            row = conn.execute(
                select(job_queue)
                .where(ready)
                .order_by(job_queue.c.run_at.asc(), job_queue.c.created_at.asc())
                .limit(1)
            ).first()
            if row is None:
                return None

            job = self._row_to_job(row)
            conn.execute(
                sa_update(job_queue)
                .where(job_queue.c.id == job["id"])
                .where(or_(job_queue.c.status == "queued", job_queue.c.status == "retry"))
                .values(
                    status="running",
                    attempts=job["attempts"] + 1,
                    locked_at=now,
                    started_at=now,
                    updated_at=now,
                )
            )
            claimed = conn.execute(select(job_queue).where(job_queue.c.id == job["id"])).first()
        return self._row_to_job(claimed)

    def mark_succeeded(self, job_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()
        with self._engine.begin() as conn:
            conn.execute(
                sa_update(job_queue)
                .where(job_queue.c.id == job_id)
                .values(
                    status="succeeded",
                    result=result,
                    last_error=None,
                    finished_at=now,
                    updated_at=now,
                )
            )
            row = conn.execute(select(job_queue).where(job_queue.c.id == job_id)).first()
        return self._row_to_job(row)

    def mark_failed(self, job_id: str, error: str) -> Dict[str, Any]:
        now = time.time()
        with self._engine.begin() as conn:
            row = conn.execute(select(job_queue).where(job_queue.c.id == job_id)).first()
            if row is None:
                raise KeyError(f"Job nao encontrado: {job_id}")
            job = self._row_to_job(row)
            dead = job["attempts"] >= job["max_attempts"]
            next_status = "dead" if dead else "retry"
            delay = self.retry_backoff_seconds * max(1, job["attempts"])
            conn.execute(
                sa_update(job_queue)
                .where(job_queue.c.id == job_id)
                .values(
                    status=next_status,
                    last_error=error[:2000],
                    run_at=now + delay if not dead else job["run_at"],
                    finished_at=now if dead else None,
                    updated_at=now,
                )
            )
            updated = conn.execute(select(job_queue).where(job_queue.c.id == job_id)).first()
        return self._row_to_job(updated)

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._engine.connect() as conn:
            row = conn.execute(select(job_queue).where(job_queue.c.id == job_id)).first()
        return self._row_to_job(row) if row else None

    def list(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        stmt = select(job_queue)
        if status:
            stmt = stmt.where(job_queue.c.status == status)
        stmt = stmt.order_by(job_queue.c.created_at.desc()).limit(max(1, min(limit, 200)))
        with self._engine.connect() as conn:
            rows = conn.execute(stmt).all()
        return [self._row_to_job(row) for row in rows]
