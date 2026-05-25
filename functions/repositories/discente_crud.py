# functions/repositories/discente_crud.py
from typing import Dict
from functions.repositories.base import BaseCRUD

class DiscenteCRUD(BaseCRUD):
    def __init__(self):
        super().__init__("discentes")

    def create(self, data: Dict) -> Dict:
        data.setdefault("status", "ATIVO")
        return super().create(data)
