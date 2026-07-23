"""Registro de parsers de formato indexados pela versão do envelope."""

from __future__ import annotations

from typing import Callable, Optional

from ..models import Envelope, RawPayload

# Um parser recebe o envelope e devolve o payload bruto interpretado.
ParseFn = Callable[[Envelope], RawPayload]


class Format:
    def __init__(self, version: int, name: str, parse: ParseFn) -> None:
        self.version = version
        self.name = name
        self.parse = parse


_FORMATS: dict[int, Format] = {}


def register_format(version: int, name: str) -> Callable[[ParseFn], ParseFn]:
    def decorator(fn: ParseFn) -> ParseFn:
        _FORMATS[version] = Format(version, name, fn)
        return fn

    return decorator


def get_format(version: int) -> Optional[Format]:
    return _FORMATS.get(version)


def supported_versions() -> list[int]:
    return sorted(_FORMATS)
