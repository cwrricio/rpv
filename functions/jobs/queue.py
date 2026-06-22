from functions.jobs.ports import JobQueuePort

_INSTANCE: JobQueuePort | None = None


def get_job_queue() -> JobQueuePort:
    """Retorna a fila ativa (singleton), isolando o adaptador concreto."""
    global _INSTANCE
    if _INSTANCE is not None:
        return _INSTANCE

    from functions.jobs.sqlalchemy_queue import SQLAlchemyJobQueue

    queue = SQLAlchemyJobQueue()
    queue.init_schema()
    _INSTANCE = queue
    return _INSTANCE
