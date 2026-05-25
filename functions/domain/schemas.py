from __future__ import annotations

from typing import Any

from pydantic import BaseModel, validator

from functions.domain.types import StatusPesquisa, TipoDocente


class APIModel(BaseModel):
    class Config:
        extra = "allow"
        use_enum_values = True

    def to_payload(self) -> dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump(mode="json", exclude_none=True, exclude_unset=True)
        return self.dict(exclude_none=True, exclude_unset=True)


class DocenteBase(APIModel):
    nome: str | None = None
    name: str | None = None
    tipo: TipoDocente | None = None
    orcid: str | None = None
    lattes: str | None = None
    scholar: str | None = None
    instagram: str | None = None
    linkedin: str | None = None
    research: str | None = None
    hIndex: int | str | None = None
    h5Index: int | str | None = None
    h_index: int | str | None = None
    h5_index: int | str | None = None

    @validator("tipo", pre=True)
    @classmethod
    def normalize_tipo(cls, value):
        if value in (None, ""):
            return None
        if isinstance(value, TipoDocente):
            return value
        if isinstance(value, str):
            return value.upper()
        return value


class DocenteCreate(DocenteBase):
    pass


class DocenteOut(DocenteBase):
    id: str


class DiscenteBase(APIModel):
    nome: str | None = None
    name: str | None = None
    status: str | None = None
    advisor: str | None = None
    orientador_id: str | None = None
    research: str | None = None
    entryDate: str | None = None
    qualifDate: str | None = None
    defenseDate: str | None = None
    data_ingresso: str | None = None
    data_qualificacao: str | None = None
    data_defesa: str | None = None


class DiscenteCreate(DiscenteBase):
    pass


class DiscenteOut(DiscenteBase):
    id: str


class ProjetoBase(APIModel):
    titulo: str | None = None
    name: str | None = None
    descricao: str | None = None
    research: str | None = None
    status: StatusPesquisa | None = None
    coordinator: Any | None = None
    teachers: Any | None = None
    students: Any | None = None
    dataInicio: str | None = None
    data_inicio: str | None = None
    dataFim: str | None = None
    data_fim: str | None = None

    @validator("status", pre=True)
    @classmethod
    def normalize_status(cls, value):
        if value in (None, ""):
            return None
        if isinstance(value, StatusPesquisa):
            return value
        if isinstance(value, str):
            return value.upper()
        return value


class ProjetoCreate(ProjetoBase):
    pass


class ProjetoOut(ProjetoBase):
    id: str
