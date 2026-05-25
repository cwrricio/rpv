# functions/repositories/docente_crud.py
from typing import Dict, List
from functions.domain.types import TipoDocente
from functions.repositories.base import BaseCRUD

class DocenteCRUD(BaseCRUD):
    def __init__(self):
        super().__init__("docentes")

    # regras simples
    def create(self, data: Dict) -> Dict:
        tipo = (data.get("tipo") or "PERMANENTE").upper()
        try:
            tipo_docente = TipoDocente(tipo)
        except ValueError as exc:
            validos = sorted(item.value for item in TipoDocente)
            raise ValueError(f"tipo inválido. Use um de {validos}") from exc
        data["tipo"] = tipo_docente.value
        return super().create(data)

    def find_by_orcid(self, orcid: str) -> List[Dict]:
        node = self.ref()
        snaps = node.order_by_child("orcid").equal_to(orcid).get() or {}
        return [{"id": k, **v} for k, v in snaps.items() if isinstance(v, dict)]
