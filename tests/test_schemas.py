"""Testes unitários dos schemas Pydantic (Frente 4.5).

Verificam normalização de enums, rejeição de valores inválidos e o
comportamento de to_payload(). Nenhum acesso ao Firebase.
"""

import pytest
from pydantic import ValidationError

from functions.domain.schemas import (
    DiscenteCreate,
    DocenteCreate,
    DocenteOut,
    ProjetoCreate,
)


# --------------------------------------------------------------------------- #
# DocenteCreate / TipoDocente
# --------------------------------------------------------------------------- #
def test_docente_tipo_valido():
    d = DocenteCreate(nome="Maria", tipo="PERMANENTE")
    assert d.tipo == "PERMANENTE"  # use_enum_values=True -> string


def test_docente_tipo_normaliza_caixa():
    d = DocenteCreate(nome="Maria", tipo="permanente")
    assert d.tipo == "PERMANENTE"


@pytest.mark.parametrize("invalido", ["INVALIDO", "professor", "ADJUNTO", "123"])
def test_docente_tipo_invalido_e_rejeitado(invalido):
    with pytest.raises(ValidationError):
        DocenteCreate(nome="Maria", tipo=invalido)


@pytest.mark.parametrize("vazio", [None, ""])
def test_docente_tipo_vazio_vira_none(vazio):
    d = DocenteCreate(nome="Maria", tipo=vazio)
    assert d.tipo is None


def test_docente_to_payload_exclui_none_e_unset():
    d = DocenteCreate(nome="Maria", tipo="PERMANENTE")
    payload = d.to_payload()
    assert payload == {"nome": "Maria", "tipo": "PERMANENTE"}


# --------------------------------------------------------------------------- #
# DocenteOut
# --------------------------------------------------------------------------- #
def test_docente_out_exige_id():
    with pytest.raises(ValidationError):
        DocenteOut(nome="Maria")  # falta o campo obrigatório 'id'


def test_docente_out_com_id():
    out = DocenteOut(id="abc123", nome="Maria", tipo="COLABORADOR")
    assert out.id == "abc123"
    assert out.tipo == "COLABORADOR"


# --------------------------------------------------------------------------- #
# ProjetoCreate / StatusPesquisa
# --------------------------------------------------------------------------- #
def test_projeto_status_normaliza():
    p = ProjetoCreate(titulo="Projeto X", status="em_andamento")
    assert p.status == "EM_ANDAMENTO"


def test_projeto_status_invalido_rejeitado():
    with pytest.raises(ValidationError):
        ProjetoCreate(titulo="Projeto X", status="CANCELADO")


# --------------------------------------------------------------------------- #
# DiscenteCreate — campo extra permitido (Config.extra = "allow")
# --------------------------------------------------------------------------- #
def test_discente_aceita_campo_extra():
    d = DiscenteCreate(nome="Ana", campo_inesperado="valor")
    assert d.to_payload()["campo_inesperado"] == "valor"
