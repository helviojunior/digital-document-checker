"""Utilitários compartilhados pelos handlers de documento."""

from __future__ import annotations

from typing import Optional

from ..models import RawPayload, Template
from .base import DocumentData


def map_fields(
    data: DocumentData,
    payload: RawPayload,
    template: Optional[Template],
    default_order: list[str],
) -> DocumentData:
    """Preenche ``data`` a partir dos valores brutos.

    A ordem dos campos vem do template (quando disponível) ou de
    ``default_order``. Atributos existentes na dataclass são atribuídos; todos
    os campos ficam também em ``data.fields``. Valores excedentes vão para
    ``data.fields['_extras']``.
    """
    order = template.field_names if template and template.field_names else default_order
    values = payload.field_values

    data.raw_fields = list(values)
    for index, name in enumerate(order):
        value = values[index].strip() if index < len(values) else ""
        data.fields[name] = value
        if hasattr(data, name):
            setattr(data, name, value)

    extras = values[len(order):]
    if extras:
        data.fields["_extras"] = extras  # type: ignore[assignment]
    return data
