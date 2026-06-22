import pytest

pytest.importorskip("sqlalchemy")

from functions.jobs.sqlalchemy_queue import SQLAlchemyJobQueue


@pytest.fixture
def queue():
    q = SQLAlchemyJobQueue("sqlite+pysqlite:///:memory:", retry_backoff_seconds=0)
    q.init_schema()
    return q


def test_enqueue_com_idempotency_key_retorna_mesmo_job(queue):
    first = queue.enqueue(
        "harvest.batch",
        {"items": [{"name": "Alice"}]},
        idempotency_key="idem-1",
    )
    second = queue.enqueue(
        "harvest.batch",
        {"items": [{"name": "Alice"}]},
        idempotency_key="idem-1",
    )

    assert second["id"] == first["id"]
    assert queue.list()[0]["id"] == first["id"]


def test_claim_next_e_mark_succeeded(queue):
    job = queue.enqueue("harvest.batch", {"items": [{"name": "Alice"}]})

    claimed = queue.claim_next()
    assert claimed["id"] == job["id"]
    assert claimed["status"] == "running"
    assert claimed["attempts"] == 1

    done = queue.mark_succeeded(claimed["id"], {"ok": True})

    assert done["status"] == "succeeded"
    assert done["result"] == {"ok": True}
    assert queue.claim_next() is None


def test_mark_failed_faz_retry_e_depois_dead_letter(queue):
    job = queue.enqueue("harvest.batch", {"items": [{"name": "Alice"}]}, max_attempts=2)

    first = queue.claim_next()
    retry = queue.mark_failed(first["id"], "timeout")
    assert retry["status"] == "retry"
    assert retry["last_error"] == "timeout"

    second = queue.claim_next()
    dead = queue.mark_failed(second["id"], "timeout again")
    assert dead["status"] == "dead"
    assert dead["last_error"] == "timeout again"

    assert queue.list(status="dead")[0]["id"] == job["id"]


def test_worker_run_once_marca_sucesso(monkeypatch, queue):
    from functions.jobs import worker

    job = queue.enqueue("fake.task", {"x": 1})
    monkeypatch.setattr(worker, "get_job_queue", lambda: queue)
    monkeypatch.setattr(worker, "run_task", lambda task_name, payload: {"task": task_name, "payload": payload})

    worked = worker.run_once()

    assert worked is True
    stored = queue.get(job["id"])
    assert stored["status"] == "succeeded"
    assert stored["result"] == {"task": "fake.task", "payload": {"x": 1}}


def test_worker_run_once_marca_retry_em_falha(monkeypatch, queue):
    from functions.jobs import worker

    job = queue.enqueue("fake.task", {"x": 1}, max_attempts=2)

    def fail(_task_name, _payload):
        raise RuntimeError("boom")

    monkeypatch.setattr(worker, "get_job_queue", lambda: queue)
    monkeypatch.setattr(worker, "run_task", fail)

    worked = worker.run_once()

    assert worked is True
    stored = queue.get(job["id"])
    assert stored["status"] == "retry"
    assert stored["last_error"] == "boom"
