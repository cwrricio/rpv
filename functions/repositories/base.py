# functions/repositories/base.py
from typing import Optional, Dict, Any
from fastapi import HTTPException
import traceback

from functions.repositories.ports import StoragePort
from functions.adapters import get_storage


class BaseCRUD:
    # Defina nas subclasses: path_root = "nome_do_no"
    path_root: Optional[str] = None

    def __init__(self, path_root: Optional[str] = None, storage: Optional[StoragePort] = None):
        if path_root:
            self.path_root = path_root
        if not self.path_root:
            raise RuntimeError(f"{self.__class__.__name__}: 'path_root' não definido")
        # Injeção de dependência: default = adaptador ativo (Firebase hoje).
        # Permite injetar um StoragePort fake em testes ou trocar por Postgres.
        self.storage: StoragePort = storage or get_storage()

    def ref(self):
        """Escape hatch para consultas ainda não portadas ao StoragePort.

        Só funciona com adaptadores que expõem `raw_ref` (Firebase). Mantido
        por compatibilidade com queries específicas do RTDB (ex.: DocenteCRUD.
        find_by_orcid). Cada chamada é dívida de migração a ser eliminada.
        """
        raw = getattr(self.storage, "raw_ref", None)
        if raw is None:
            raise NotImplementedError(
                f"O backend ativo não suporta queries diretas em '{self.path_root}'. "
                "Porte esta consulta para o StoragePort."
            )
        return raw(self.path_root)

    # --------- operações ---------
    def create(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self.storage.create(self.path_root, obj)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, f"Erro ao criar: {e}")

    def list(self):
        try:
            return self.storage.list(self.path_root)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, f"Erro ao listar: {e}")

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        try:
            return self.storage.get(self.path_root, id)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, f"Erro ao obter {id}: {e}")

    def update(self, id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            return self.storage.update(self.path_root, id, patch)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, f"Erro ao atualizar {id}: {e}")

    def delete(self, id: str) -> bool:
        try:
            return self.storage.delete(self.path_root, id)
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, f"Erro ao remover {id}: {e}")
