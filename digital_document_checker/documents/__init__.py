"""Submódulos de documento e seu registro.

Para adicionar um novo tipo de documento, crie um :class:`DocumentHandler`
e registre-o com :func:`register_handler`.
"""

from __future__ import annotations

from typing import Optional

from ..models import Template
from .base import DocumentData, DocumentHandler
from .cin import CINData, CINHandler
from .cnh import CNHData, CNHHandler
from .dni import DNIData, DNIHandler
from .rg import RGData, RGHandler
from .generic import GenericHandler

_HANDLERS: list[DocumentHandler] = []
_GENERIC = GenericHandler()


def register_handler(handler: DocumentHandler, *, prepend: bool = False) -> None:
    if prepend:
        _HANDLERS.insert(0, handler)
    else:
        _HANDLERS.append(handler)


def find_handler(template_id: int, template: Optional[Template]) -> DocumentHandler:
    for handler in _HANDLERS:
        if handler.matches(template_id, template):
            return handler
    return _GENERIC


# handlers embarcados
register_handler(CNHHandler())
register_handler(DNIHandler())
register_handler(RGHandler())


__all__ = [
    "DocumentData",
    "DocumentHandler",
    "CINData",
    "CINHandler",
    "CNHData",
    "CNHHandler",
    "DNIData",
    "DNIHandler",
    "RGData",
    "RGHandler",
    "GenericHandler",
    "register_handler",
    "find_handler",
]
