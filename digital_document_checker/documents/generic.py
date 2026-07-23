"""Handler genérico: usado quando nenhum submódulo específico reconhece o tipo.

Mapeia os valores brutos aos nomes de campo declarados pelo template (quando
existir), preservando todos os dados disponíveis.
"""

from __future__ import annotations

from typing import Optional

from ..models import RawPayload, Template
from .base import DocumentData, DocumentHandler


class GenericHandler(DocumentHandler):
    type_name = "generic"
    display_name = "Documento Digital"

    def matches(self, template_id: int, template: Optional[Template]) -> bool:
        return True

    def build(self, payload: RawPayload, template: Optional[Template]) -> DocumentData:
        values = payload.field_values
        fields: dict[str, str] = {}
        if template and template.field_names:
            for index, name in enumerate(template.field_names):
                fields[name] = values[index] if index < len(values) else ""
            extras = values[len(template.field_names):]
            if extras:
                fields["_extras"] = extras  # type: ignore[assignment]
        else:
            for index, value in enumerate(values):
                fields[f"field_{index}"] = value
        return DocumentData(raw_fields=list(values), fields=fields)
