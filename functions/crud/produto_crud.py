# functions/crud/produto_crud.py
from typing import Dict
from functions.crud.base import BaseCRUD
from functions.crud.validators import validate_doi, normalize_doi_url

SUBTIPOS_BIB = {"ARTIGO", "CAPITULO", "ANAIS", "LIVRO"}

class ProdutoCRUD(BaseCRUD):
    def __init__(self):
        super().__init__("produtos")

    def create(self, data: Dict) -> Dict:
        data.setdefault("tipo", "BIBLIOGRAFICA")
        subtipo = (data.get("subtipo") or "ARTIGO").upper()
        if data["tipo"] == "BIBLIOGRAFICA" and subtipo not in SUBTIPOS_BIB:
            raise ValueError(f"subtipo inválido para bibliográfica. Use {sorted(SUBTIPOS_BIB)}")
        data["subtipo"] = subtipo

        doi = data.get("doi")
        if doi and not validate_doi(doi):
            raise ValueError("DOI inválido (ex.: 10.1000/xyz123)")
        # url preferencial a partir do DOI, se não mandar 'url'
        data.setdefault("url", normalize_doi_url(doi))

        return super().create(data)

    def update(self, id_: str, data: Dict):
        if "doi" in data and data["doi"] and not validate_doi(data["doi"]):
            raise ValueError("DOI inválido (ex.: 10.1000/xyz123)")
        if "url" not in data and data.get("doi"):
            data["url"] = normalize_doi_url(data["doi"])
        return super().update(id_, data)
