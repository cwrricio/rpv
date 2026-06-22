from typing import Any, Callable, Dict

TaskHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


def harvest_batch(payload: Dict[str, Any]) -> Dict[str, Any]:
    from functions.api_routes.harvest_authors import harvest_batch as run_harvest_batch

    return run_harvest_batch(payload)


TASKS: dict[str, TaskHandler] = {
    "harvest.batch": harvest_batch,
}


def run_task(task_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        handler = TASKS[task_name]
    except KeyError as exc:
        raise ValueError(f"Task desconhecida: {task_name}") from exc
    return handler(payload)
