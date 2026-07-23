"""Submódulo do DNI (Documento Nacional de Identificação) — TSE.

Templates ``8``, ``9`` (grupo ``bb7a9a25-…``) e ``73`` (grupo ``36bbdb5f-…``).
Emitido, no app oficial, no formato de envelope versão 3 (basE91 + foto BPG).
Os campos são separados por ``^`` na ordem declarada pelo template.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..models import RawPayload, Template
from ._helpers import map_fields
from .base import DocumentData, DocumentHandler

# União dos campos dos templates 8/9/73 (a ordem real vem sempre do template).
FIELD_ORDER_DEFAULT = [
    "numero_icn",
    "nome",
    "matricula_nascimento",
    "data_nascimento",
    "filiacao_1",
    "filiacao_2",
    "naturalidade",
    "uf",
    "cpf",
    "titulo_eleitor",
    "orgao_expedidor",
    "data_expedicao",
    "situacao_registro",
    "data_ultima_atualizacao",
]


@dataclass
class DNIData(DocumentData):
    numero_icn: Optional[str] = None
    nome: Optional[str] = None
    matricula_nascimento: Optional[str] = None
    data_nascimento: Optional[str] = None
    filiacao_1: Optional[str] = None
    filiacao_2: Optional[str] = None
    naturalidade: Optional[str] = None
    uf: Optional[str] = None
    cpf: Optional[str] = None
    titulo_eleitor: Optional[str] = None
    orgao_expedidor: Optional[str] = None
    data_expedicao: Optional[str] = None
    situacao_registro: Optional[str] = None
    data_ultima_atualizacao: Optional[str] = None
    # campos exclusivos do template 73
    munic_nascimento: Optional[str] = None
    uf_nascimento: Optional[str] = None
    data_emissao_dni: Optional[str] = None

    @property
    def cpf_formatado(self) -> Optional[str]:
        if not self.cpf:
            return None
        digits = re.sub(r"\D", "", self.cpf)
        if len(digits) != 11:
            return self.cpf
        return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"

    @property
    def filiacao(self) -> list[str]:
        return [f for f in (self.filiacao_1, self.filiacao_2) if f]


class DNIHandler(DocumentHandler):
    type_name = "dni"
    display_name = "Documento Nacional de Identificação"
    template_ids = (8, 9, 73)

    def matches(self, template_id: int, template: Optional[Template]) -> bool:
        if template_id in self.template_ids:
            return True
        return bool(template and template.name and template.name.strip().upper() == "DNI")

    def build(self, payload: RawPayload, template: Optional[Template]) -> DNIData:
        return map_fields(DNIData(), payload, template, FIELD_ORDER_DEFAULT)
