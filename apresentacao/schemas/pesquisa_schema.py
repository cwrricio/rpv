from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from functions.domain.types import StatusPesquisa

class PesquisaIn(BaseModel):
    titulo: str = Field(min_length=3)
    projeto_id: str
    linha_id: str
    orientador_id: str
    discente_id: str
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None

class PesquisaOut(PesquisaIn):
    id: str
    status: StatusPesquisa

class PesquisaList(BaseModel):
    items: List[PesquisaOut]
