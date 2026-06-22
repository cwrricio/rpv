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
        node.child(key).set(obj)
        return {"id": key, **obj}

    def list(self, path_root: str) -> List[Dict[str, Any]]:
        data = self._ref(path_root).get() or {}
        if isinstance(data, dict):
            out = []
            for k, v in data.items():
                if isinstance(v, dict):
                    out.append({"id": k, **v})
                else:
                    out.append({"id": k, "value": v})
            return out
        if isinstance(data, list):
            # raríssimo no RTDB para coleções, mas suportado
            return [
                {"id": str(i), **(v if isinstance(v, dict) else {"value": v})}
                for i, v in enumerate(data)
            ]
        return []

    def get(self, path_root: str, id: str) -> Optional[Dict[str, Any]]:
        v = self._ref(path_root).child(id).get()
        if v is None:
            return None
        return {"id": id, **v} if isinstance(v, dict) else {"id": id, "value": v}

    def update(self, path_root: str, id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        node = self._ref(path_root).child(id)
        if node.get() is None:
            return None
        node.update(patch)
        v = node.get() or {}
        return {"id": id, **v} if isinstance(v, dict) else {"id": id, "value": v}

    def delete(self, path_root: str, id: str) -> bool:
        node = self._ref(path_root).child(id)
        if node.get() is None:
            return False
        node.delete()
        return True

    def find_by_field(self, path_root: str, field: str, value: Any) -> List[Dict[str, Any]]:
        snaps = self._ref(path_root).order_by_child(field).equal_to(value).get() or {}
        return [
            {"id": k, **v}
            for k, v in snaps.items()
            if isinstance(v, dict)
        ]
