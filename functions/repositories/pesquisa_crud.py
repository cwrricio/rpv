from functions.repositories.base import BaseCRUD

class PesquisaCRUD(BaseCRUD):
    path_root = "pesquisas"  # ajuste se seu nó no RTDB tiver outro nome
