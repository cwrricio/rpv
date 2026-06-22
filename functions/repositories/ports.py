# functions/repositories/ports.py
"""
Porta de armazenamento (StoragePort) — interface da camada de persistência.

Esta porta isola as regras de negócio (repositories/services) do provedor de
banco de dados concreto. Qualquer adaptador (Firebase RTDB hoje, PostgreSQL
amanhã) que implemente este contrato pode ser injetado sem reescrever os CRUDs.

Modelo de dados: coleções identificadas por `path_root` (ex.: "autores",
"pesquisas"), cada item com um `id` string e um corpo (dict). Esse formato
espelha os nós do RTDB e facilita a paridade durante a migração.
"""
from typing import Protocol, Optional, Dict, Any, List, runtime_checkable


@runtime_checkable
class StoragePort(Protocol):
    """Contrato mínimo de persistência consumido por BaseCRUD."""

    def create(self, path_root: str, obj: Dict[str, Any]) -> Dict[str, Any]:
        """Cria um item na coleção e retorna {"id": ..., **obj}."""
        ...

    def list(self, path_root: str) -> List[Dict[str, Any]]:
        """Lista todos os itens da coleção como [{"id": ..., ...}, ...]."""
        ...

    def get(self, path_root: str, id: str) -> Optional[Dict[str, Any]]:
        """Retorna o item por id ou None se não existir."""
        ...

    def update(self, path_root: str, id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Aplica patch parcial; retorna o item atualizado ou None se não existir."""
        ...

    def delete(self, path_root: str, id: str) -> bool:
        """Remove o item; retorna True se removido, False se não existia."""
        ...
