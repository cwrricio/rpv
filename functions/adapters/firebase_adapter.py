# functions/adapters/firebase_adapter.py
"""
Adaptador de armazenamento para Firebase Realtime Database.

Encapsula TODA a forma de acesso específica do RTDB (push/child/set/get) que
antes vivia espalhada em BaseCRUD. É o único lugar (junto de common/dbref.py)
onde a API proprietária do Firebase pode aparecer no pacote `functions/`.
"""
from typing import Optional, Dict, Any, List

from functions.common.dbref import ref
from functions.repositories.ports import StoragePort


class FirebaseRTDBAdapter(StoragePort):
    """Implementa StoragePort sobre o Firebase RTDB."""

    @staticmethod
    def _payload(obj: Dict[str, Any]) -> Dict[str, Any]:
        return {k: v for k, v in obj.items() if k != "id"}

    @classmethod
    def _with_id(cls, row_id: str, data: Any) -> Dict[str, Any]:
        if isinstance(data, dict):
            return {"id": row_id, **cls._payload(data)}
        return {"id": row_id, "value": data}

    def _ref(self, path_root: str):
        return ref(path_root)

    def raw_ref(self, path_root: str):
        """Escape hatch para queries específicas do RTDB (ex.: order_by_child).

        Usado por consultas que ainda não foram portadas para o StoragePort.
        Cada uso é um item de migração pendente (ver docs/DATA_MODEL.md).
        """
        return ref(path_root)

    def create(self, path_root: str, obj: Dict[str, Any]) -> Dict[str, Any]:
        node = self._ref(path_root)
        key = node.push().key
        payload = self._payload(obj)
        node.child(key).set(payload)
        return {"id": key, **payload}

    def upsert(self, path_root: str, id: str, obj: Dict[str, Any]) -> Dict[str, Any]:
        payload = self._payload(obj)
        self._ref(path_root).child(id).set(payload)
        return {"id": id, **payload}

    def list(self, path_root: str) -> List[Dict[str, Any]]:
        data = self._ref(path_root).get() or {}
        if isinstance(data, dict):
            out = []
            for k, v in data.items():
                out.append(self._with_id(k, v))
            return out
        if isinstance(data, list):
            # raríssimo no RTDB para coleções, mas suportado
            return [
                self._with_id(str(i), v)
                for i, v in enumerate(data)
            ]
        return []

    def get(self, path_root: str, id: str) -> Optional[Dict[str, Any]]:
        v = self._ref(path_root).child(id).get()
        if v is None:
            return None
        return self._with_id(id, v)

    def update(self, path_root: str, id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        node = self._ref(path_root).child(id)
        if node.get() is None:
            return None
        node.update(self._payload(patch))
        v = node.get() or {}
        return self._with_id(id, v)

    def delete(self, path_root: str, id: str) -> bool:
        node = self._ref(path_root).child(id)
        if node.get() is None:
            return False
        node.delete()
        return True

    def find_by_field(self, path_root: str, field: str, value: Any) -> List[Dict[str, Any]]:
        snaps = self._ref(path_root).order_by_child(field).equal_to(value).get() or {}
        return [
            self._with_id(k, v)
            for k, v in snaps.items()
            if isinstance(v, dict)
        ]
