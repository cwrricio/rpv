# functions/crud/base.py
from typing import Optional, Dict, Any
from fastapi import HTTPException
import traceback

def _db():
    from config.firebase_admin_init import init_firebase
    from firebase_admin import db
    init_firebase()
    return db

class BaseCRUD:
    # Defina nas subclasses: path_root = "nome_do_no"
    path_root: Optional[str] = None

    def __init__(self, path_root: Optional[str] = None):
        if path_root:
            self.path_root = path_root
        if not self.path_root:
            raise RuntimeError(f"{self.__class__.__name__}: 'path_root' não definido")

    # referência raiz do nó
    def ref(self):
        return _db().reference(self.path_root)

    # --------- operações ---------
    def create(self, obj: Dict[str, Any]) -> Dict[str, Any]:
        try:
            key = self.ref().push().key
            self.ref().child(key).set(obj)
            return {"id": key, **obj}
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, f"Erro ao criar: {e}")

    def list(self):
        try:
            data = self.ref().get() or {}
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
                return [{"id": str(i), **(v if isinstance(v, dict) else {"value": v})}
                        for i, v in enumerate(data)]
            return []
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, f"Erro ao listar: {e}")

    def get(self, id: str) -> Optional[Dict[str, Any]]:
        try:
            v = self.ref().child(id).get()
            if v is None:
                return None
            return {"id": id, **v} if isinstance(v, dict) else {"id": id, "value": v}
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, f"Erro ao obter {id}: {e}")

    def update(self, id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            node = self.ref().child(id)
            if node.get() is None:
                return None
            node.update(patch)
            v = node.get() or {}
            return {"id": id, **v} if isinstance(v, dict) else {"id": id, "value": v}
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, f"Erro ao atualizar {id}: {e}")

    def delete(self, id: str) -> bool:
        try:
            node = self.ref().child(id)
            if node.get() is None:
                return False
            node.delete()
            return True
        except Exception as e:
            traceback.print_exc()
            raise HTTPException(500, f"Erro ao remover {id}: {e}")
