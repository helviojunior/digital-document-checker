"""Contrato dos submódulos de documento.

Cada tipo de documento (CNH, DNI, ...) fornece um :class:`DocumentHandler`
capaz de reconhecer seus ``template_id`` e de transformar os campos brutos em
um objeto de dados tipado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from ..models import RawPayload, Template


@dataclass
class DocumentData:
    """Base para os dados tipados de um documento.

    Subclasses adicionam atributos nomeados. ``extra`` guarda campos que o
    template declara mas o handler não mapeou explicitamente.
    """

    raw_fields: list[str] = field(default_factory=list)
    fields: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = {k: v for k, v in self.__dict__.items() if k not in {"raw_fields"}}
        return out


class DocumentHandler:
    """Interface base de um submódulo de documento."""

    #: nome curto/estável do tipo (ex.: ``"cnh"``).
    type_name: str = "unknown"
    #: rótulo legível (ex.: ``"Carteira Nacional de Habilitação"``).
    display_name: str = "Documento Digital"
    #: ``template_id`` conhecidos deste tipo.
    template_ids: tuple[int, ...] = ()

    def matches(self, template_id: int, template: Optional[Template]) -> bool:
        if template_id in self.template_ids:
            return True
        if template is not None and template.name:
            return template.name.strip().upper() == self.display_name.upper()
        return False

    def build(
        self, payload: RawPayload, template: Optional[Template]
    ) -> DocumentData:  # pragma: no cover - implementado nas subclasses
        raise NotImplementedError
