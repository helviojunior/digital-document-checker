"""Submódulo da CIN — Carteira de Identidade Nacional (MJSP).

O QRCode impresso no verso da CIN é um **JWT assinado** (ES512 / P-521) e não
o envelope binário do padrão VIO/SERPRO. Estrutura reproduzida do app oficial
``identidade-nacional`` 1.19.0 (``processQrCode``)::

    {
      "iss": "MJSP",                                  # emissor obrigatório
      "cpf": "12345678901",                           # obrigatório
      "dns": "01/01/1990",                            # data de nascimento
      "dvd": "01/01/2036",                            # data de validade
      "url": "https://.../<uuid>"                     # termina com um UUID
    }

Offline o app 1.19.0 exibe apenas **CPF** e **data de nascimento**; os demais
dados (nome, filiação, sexo...) só existem na leitura *online*, obtidos da API
do MJSP a partir do ``uuid`` extraído da ``url``.

A claim ``dvd`` foi observada em uma CIN real e corresponde à "Validade /
Expiry" impressa no cartão — o app já traz o rótulo ``dateValid`` ("DATA DE
VALIDADE") em ``commonStrings.qrCodeScreen.validateOff``, mas ainda não a
renderiza. Aqui ela é lida e usada para o cálculo de expiração.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .base import DocumentData, DocumentHandler

#: Emissor exigido pelo app (``payload.iss === 'MJSP'``).
EXPECTED_ISSUER = "MJSP"

#: ``url.match(/\/([0-9a-fA-F]{8}-...-[0-9a-fA-F]{12})$/)`` no app.
UUID_IN_URL_RE = re.compile(
    r"/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)

#: Claims mapeadas para atributos nomeados; as demais vão para ``outras_claims``.
KNOWN_CLAIMS = ("iss", "cpf", "dns", "dvd", "url")


@dataclass
class CINData(DocumentData):
    """Dados legíveis offline do QRCode da CIN."""

    iss: Optional[str] = None
    cpf: Optional[str] = None
    #: ``dns`` no JWT — rotulado "DATA DE NASCIMENTO" na tela offline do app.
    data_nascimento: Optional[str] = None
    #: ``dvd`` no JWT — a "Validade / Expiry" impressa no cartão.
    data_validade: Optional[str] = None
    url: Optional[str] = None
    #: UUID extraído do final da ``url``; é a chave da consulta online.
    uuid: Optional[str] = None
    outras_claims: dict[str, Any] = field(default_factory=dict)

    @property
    def cpf_formatado(self) -> Optional[str]:
        """CPF com a máscara ``999.999.999-99`` usada pelo app."""
        if not self.cpf:
            return None
        digits = re.sub(r"\D", "", self.cpf)
        if len(digits) != 11:
            return self.cpf
        return f"{digits[0:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:11]}"


class CINHandler(DocumentHandler):
    """Handler da CIN.

    Não participa de :func:`~digital_document_checker.documents.find_handler`:
    a CIN não tem ``template_id`` — ela é reconhecida pelo próprio formato do
    QRCode (JWS compacto com ``iss`` = ``MJSP``).
    """

    type_name = "cin"
    display_name = "Carteira de Identidade Nacional"
    template_ids = ()

    def matches(self, template_id: int, template: Optional[Any]) -> bool:
        return False

    def build_from_claims(self, claims: dict[str, Any]) -> CINData:
        """Transforma as claims do JWT no objeto tipado."""
        data = CINData()
        data.iss = claims.get("iss")
        data.cpf = claims.get("cpf")
        data.data_nascimento = claims.get("dns")
        data.data_validade = claims.get("dvd")
        data.url = claims.get("url")

        if isinstance(data.url, str):
            match = UUID_IN_URL_RE.search(data.url)
            if match:
                data.uuid = match.group(1)

        data.outras_claims = {
            key: value for key, value in claims.items() if key not in KNOWN_CLAIMS
        }

        data.fields = {
            "iss": data.iss,
            "cpf": data.cpf,
            "cpf_formatado": data.cpf_formatado,
            "data_nascimento": data.data_nascimento,
            "data_validade": data.data_validade,
            "url": data.url,
            "uuid": data.uuid,
        }
        for key, value in data.outras_claims.items():
            data.fields.setdefault(key, value)

        data.raw_fields = [
            str(value) for value in (data.cpf, data.data_nascimento) if value is not None
        ]
        return data
