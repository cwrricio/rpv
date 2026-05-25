# functions/crud/projeto_crud.py
from functions.crud.base import BaseCRUD

class ProjetoCRUD(BaseCRUD):
    def __init__(self):
        super().__init__("projetos")
