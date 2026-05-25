# functions/crud/veiculo_crud.py
from typing import Dict
from functions.crud.base import BaseCRUD
from functions.crud.validators import validate_issn

class VeiculoCRUD(BaseCRUD):
    def __init__(self):
        super().__init__("veiculos")

    def create(self, data: Dict) -> Dict:
        issn = data.get("issn")
        if issn and not validate_issn(issn):
            raise ValueError("ISSN inválido. Formato esperado: NNNN-NNNX")
        return super().create(data)

    def update(self, id_: str, data: Dict):
        issn = data.get("issn")
        if issn and not validate_issn(issn):
            raise ValueError("ISSN inválido. Formato esperado: NNNN-NNNX")
        return super().update(id_, data)
