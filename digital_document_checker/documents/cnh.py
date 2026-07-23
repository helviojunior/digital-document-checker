"""Submódulo da CNH (Carteira Nacional de Habilitação) digital.

Templates ``2``, ``4`` e ``83`` do emissor SENATRAN. Os campos são separados
por ``^`` na ordem declarada pelo template.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from ..models import RawPayload, Template
from ._helpers import map_fields
from .base import DocumentData, DocumentHandler

# Ordem canônica dos campos (template 4; o 83 acrescenta ``nome_civil`` na 2ª
# posição). A ordem real é sempre lida do template quando disponível.
FIELD_ORDER_DEFAULT = [
    "nome",
    "identidade",
    "cpf",
    "data_nascimento",
    "filiacao_pai",
    "filiacao_mae",
    "permissao",
    "acc",
    "categoria",
    "numero_registro",
    "data_validade",
    "data_primeira_habilitacao",
    "observacoes",
    "local_emissao",
    "uf_emissao",
    "data_emissao",
    "numero_validacao_cnh",
    "numero_renach",
]


@dataclass
class CNHData(DocumentData):
    nome: Optional[str] = None
    nome_civil: Optional[str] = None
    identidade: Optional[str] = None
    cpf: Optional[str] = None
    data_nascimento: Optional[str] = None
    filiacao_pai: Optional[str] = None
    filiacao_mae: Optional[str] = None
    permissao: Optional[str] = None
    acc: Optional[str] = None
    categoria: Optional[str] = None
    numero_registro: Optional[str] = None
    data_validade: Optional[str] = None
    data_primeira_habilitacao: Optional[str] = None
    observacoes: Optional[str] = None
    local_emissao: Optional[str] = None
    uf_emissao: Optional[str] = None
    data_emissao: Optional[str] = None
    numero_validacao_cnh: Optional[str] = None
    numero_renach: Optional[str] = None

    @property
    def cpf_formatado(self) -> Optional[str]:
        if not self.cpf:
            return None
        digits = re.sub(r"\D", "", self.cpf)
        if len(digits) != 11:
            return self.cpf
        return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


class CNHHandler(DocumentHandler):
    type_name = "cnh"
    display_name = "Carteira Nacional de Habilitação"
    template_ids = (2, 4, 83)

    def matches(self, template_id: int, template: Optional[Template]) -> bool:
        if template_id in self.template_ids:
            return True
        return bool(template and template.name and template.name.strip().upper() == "CNH")

    def build(self, payload: RawPayload, template: Optional[Template]) -> CNHData:
        return map_fields(CNHData(), payload, template, FIELD_ORDER_DEFAULT)
