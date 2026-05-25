# functions/crud/discente_crud.py
from typing import Dict
from functions.crud.base import BaseCRUD

class DiscenteCRUD(BaseCRUD):
    def __init__(self):
        super().__init__("discentes")

    def create(self, data: Dict) -> Dict:
        data.setdefault("status", "ATIVO")
        return super().create(data)
