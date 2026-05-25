# functions/repositories/linha_crud.py
from functions.repositories.base import BaseCRUD

class LinhaCRUD(BaseCRUD):
    def __init__(self):
        super().__init__("linhas")
