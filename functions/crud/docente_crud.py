# functions/crud/docente_crud.py
from typing import Dict, List, Optional
from functions.crud.base import BaseCRUD

TIPOS_VALIDOS = {"PERMANENTE", "COLABORADOR", "VISITANTE"}

class DocenteCRUD(BaseCRUD):
    def __init__(self):
        super().__init__("docentes")

    # regras simples
    def create(self, data: Dict) -> Dict:
        tipo = (data.get("tipo") or "PERMANENTE").upper()
        if tipo not in TIPOS_VALIDOS:
            raise ValueError(f"tipo inválido. Use um de {sorted(TIPOS_VALIDOS)}")
        data["tipo"] = tipo
        return super().create(data)

    def find_by_orcid(self, orcid: str) -> List[Dict]:
        node = self._node()
        snaps = node.order_by_child("orcid").equal_to(orcid).get() or {}
        return [{"id": k, **v} for k, v in snaps.items() if isinstance(v, dict)]
