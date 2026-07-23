"""Submódulo do RG Digital (Carteira de Identidade Nacional) — GovBr.

Templates ``91`` e ``92`` (grupo ``36bbdb5f-…``). Os campos são separados por
``^`` na ordem declarada pelo template.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..models import RawPayload, Template
from ._helpers import map_fields
from .base import DocumentData, DocumentHandler

FIELD_ORDER_DEFAULT = [
    "nome",
    "nome_social",
    "cpf",
    "sexo",
    "data_nascimento",
    "nacionalidade",
    "naturalidade",
    "data_validade",
    "filiacao_1",
    "filiacao_2",
    "orgao_expedidor",
    "local_emissao",
    "data_emissao",
    "certidao",
    "hash",
]


@dataclass
class RGData(DocumentData):
    nome: Optional[str] = None
    nome_social: Optional[str] = None
    cpf: Optional[str] = None
    sexo: Optional[str] = None
    data_nascimento: Optional[str] = None
    nacionalidade: Optional[str] = None
    naturalidade: Optional[str] = None
    data_validade: Optional[str] = None
    filiacao_1: Optional[str] = None
    filiacao_2: Optional[str] = None
    orgao_expedidor: Optional[str] = None
    local_emissao: Optional[str] = None
    data_emissao: Optional[str] = None
    certidao: Optional[str] = None
    hash: Optional[str] = None

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


class RGHandler(DocumentHandler):
    type_name = "rg_digital"
    display_name = "RG Digital"
    template_ids = (91, 92)

    def matches(self, template_id: int, template: Optional[Template]) -> bool:
        if template_id in self.template_ids:
            return True
        return bool(
            template and template.name and template.name.strip().upper() == "RG DIGITAL"
        )

    def build(self, payload: RawPayload, template: Optional[Template]) -> RGData:
        return map_fields(RGData(), payload, template, FIELD_ORDER_DEFAULT)
