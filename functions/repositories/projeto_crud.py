# functions/repositories/projeto_crud.py
from functions.repositories.base import BaseCRUD

class ProjetoCRUD(BaseCRUD):
    def __init__(self):
        super().__init__("projetos")
