from __future__ import annotations

import argparse
import json
import time
import traceback

from functions.jobs.queue import get_job_queue
from functions.jobs.tasks import run_task


def run_once() -> bool:
    """Executa um job pronto. Retorna True se trabalhou."""
    queue = get_job_queue()
    job = queue.claim_next()
    if job is None:
        return False

    job_id = job["id"]
    task_name = job["task_name"]
    print(f"[worker] start job={job_id} task={task_name} attempt={job['attempts']}/{job['max_attempts']}")

    try:
        result = run_task(task_name, job["payload"] or {})
    except Exception as exc:  # noqa: BLE001 - worker precisa capturar e reclassificar falhas
        traceback.print_exc()
        updated = queue.mark_failed(job_id, str(exc))
        print(f"[worker] fail job={job_id} status={updated['status']} error={str(exc)[:200]}")
        return True

    updated = queue.mark_succeeded(job_id, result)
    print(f"[worker] ok job={job_id} status={updated['status']} result={json.dumps(result, ensure_ascii=False)[:500]}")
    return True


def run_loop(*, poll_interval: float = 2.0) -> None:
    print(f"[worker] polling interval={poll_interval}s")
    while True:
        worked = run_once()
        if not worked:
            time.sleep(poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Worker de jobs de ingestao SSQM.")
    parser.add_argument("--once", action="store_true", help="Executa no maximo um job e sai.")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Intervalo quando a fila esta vazia.")
    args = parser.parse_args()

    if args.once:
        run_once()
        return
    run_loop(poll_interval=args.poll_interval)


if __name__ == "__main__":
    main()
