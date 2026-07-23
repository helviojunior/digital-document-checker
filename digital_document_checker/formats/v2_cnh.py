"""Formato da versão 2 — usado pela CNH (classe ``j.C0659F`` no APK).

Layout do payload (após o cabeçalho hexadecimal de 10 bytes)::

    [0:2]          template_id (big-endian)
    [2:4]          tamanho dos campos codificados (i8, big-endian)
    [4:4+i8]       campos, empacotados em 6 bits/símbolo, separados por '^'
    [i9:i10]       assinatura digital (256 bytes)   i9=i8+4, i10=i8+260
    [i10:]         foto BPG (sem o magic "BPG")

Dado assinado = cabeçalho original + payload sem o bloco de assinatura::

    signed = header10 + payload[0:i9] + payload[i10:]
"""

from __future__ import annotations

from ..codecs.text import decode_6bit
from ..exceptions import ParseError
from ..models import Envelope, RawPayload
from .base import register_format

SIGNATURE_SIZE = 256


@register_format(2, "CNH")
def parse(envelope: Envelope) -> RawPayload:
    payload = envelope.payload
    if len(payload) < 4:
        raise ParseError("payload v2 muito curto para conter cabeçalho de campos")

    template_id = int.from_bytes(payload[0:2], "big")
    fields_len = int.from_bytes(payload[2:4], "big")

    i9 = fields_len + 4
    i10 = fields_len + 4 + SIGNATURE_SIZE

    if len(payload) < i9:
        raise ParseError("payload v2 truncado nos campos codificados")

    fields_raw = decode_6bit(payload[4:i9]).rstrip()

    warnings: list[str] = []
    signature = payload[i9:i10]
    if len(signature) < SIGNATURE_SIZE:
        warnings.append("bloco de assinatura incompleto")

    photo = payload[i10:] if len(payload) > i10 else b""
    photo_with_magic = b"BPG" + photo if photo else None

    # Reconstrói o dado assinado sem o bloco da assinatura.
    signed_data = envelope.raw + payload[:i9] + payload[i10:]

    field_values = fields_raw.split("^") if fields_raw else []

    return RawPayload(
        template_id=template_id,
        signed_data=signed_data,
        signature=signature,
        fields_raw=fields_raw,
        field_values=field_values,
        photo=photo_with_magic,
        warnings=warnings,
    )
