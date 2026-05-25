from enum import Enum

class StatusPesquisa(str, Enum):
    EM_ANDAMENTO = "EM_ANDAMENTO"
    QUALIFICADA  = "QUALIFICADA"
    DEFENDIDA    = "DEFENDIDA"
    ARQUIVADA    = "ARQUIVADA"

class TipoDocente(str, Enum):
    PERMANENTE   = "PERMANENTE"
    COLABORADOR  = "COLABORADOR"
    VISITANTE    = "VISITANTE"
