# functions/crud/linha_crud.py
from functions.crud.base import BaseCRUD

class LinhaCRUD(BaseCRUD):
    def __init__(self):
        super().__init__("linhas")
