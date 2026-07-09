from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class JobQueuePort(Protocol):
    """Fila portavel para jobs de ingestao/processamento."""

    def enqueue(
        self,
        task_name: str,
        payload: Dict[str, Any],
        *,
        max_attempts: int = 3,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Cria um job pendente ou retorna o existente pela chave de idempotencia."""
        ...

    def claim_next(self) -> Optional[Dict[str, Any]]:
        """Reserva o proximo job pronto para execucao."""
        ...

    def mark_succeeded(self, job_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Marca um job como concluido."""
        ...

    def mark_failed(self, job_id: str, error: str) -> Dict[str, Any]:
        """Registra falha, agenda retry ou move para dead-letter."""
        ...

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retorna um job por id."""
        ...

    def list(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Lista jobs recentes para observabilidade basica."""
        ...
