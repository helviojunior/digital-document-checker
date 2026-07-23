"""Formatos multibloco das versões 4, 5 e 6 (classes ``y1.f``/``y1.h``/``y1.j``).

O payload é dividido em blocos com prefixos de tamanho de 2 bytes::

    blocks[0] = template_id          (2 bytes)
    blocks[1] = len1                 (2 bytes)
    blocks[2] = assinatura           (len1 bytes)
    blocks[3] = len2                 (2 bytes)
    blocks[4] = bloco intermediário  (len2 bytes)
    blocks[5] = len3                 (2 bytes)
    blocks[6] = campos codificados   (len3 bytes)
    blocks[7] = restante / extra     (até o fim)

Dado assinado (ver ``.i()`` no APK)::

    signed = timestamp[4:8] + versao(1 byte)
             + blocks[0] + blocks[3] + blocks[4] + blocks[5] + blocks[6]

.. note::
   Estas versões cobrem documentos além da CNH e ainda não foram validadas
   contra amostras reais; o parsing estrutural e a extração da assinatura são
   confiáveis, mas a decodificação dos campos é *best-effort*.
"""

from __future__ import annotations

from ..codecs import base91
from ..codecs.text import decode_6bit, decode_7bit
from ..exceptions import ParseError
from ..models import Envelope, RawPayload
from .base import register_format


def _split_blocks(payload: bytes) -> list[bytes]:
    if len(payload) < 4:
        raise ParseError("payload multibloco muito curto")

    def u16(offset: int) -> int:
        return (payload[offset] << 8 | payload[offset + 1]) & 0xFFFF

    template_id = payload[0:2]
    len1 = u16(2)
    i7 = len1 + 4
    block1 = payload[4:i7]
    i8 = len1 + 6
    len2_prefix = payload[i7:i8]
    len2 = (len2_prefix[0] << 8 | len2_prefix[1]) & 0xFFFF if len(len2_prefix) == 2 else 0
    i9 = len2 + i8
    block2 = payload[i8:i9]
    i10 = i9 + 2
    len3_prefix = payload[i9:i10]
    len3 = (len3_prefix[0] << 8 | len3_prefix[1]) & 0xFFFF if len(len3_prefix) == 2 else 0
    i11 = len3 + i10
    block3 = payload[i10:i11]
    rest = payload[i11:]

    return [template_id, payload[2:4], block1, len2_prefix, block2, len3_prefix, block3, rest]


def _decode_fields(block: bytes, version: int) -> str:
    if not block:
        return ""
    if version == 4:  # y1.f → alfabeto de 7 bits
        return decode_7bit(block)
    if version == 5:  # y1.h → alfabeto de 6 bits
        return decode_6bit(block).rstrip()
    # version 6 (y1.j) → basE91 e depois 7 bits
    return decode_7bit(base91.decode(block))


def _parse(envelope: Envelope, version: int) -> RawPayload:
    payload = envelope.payload
    blocks = _split_blocks(payload)
    template_id = int.from_bytes(blocks[0], "big")
    signature = blocks[2]

    timestamp_bytes = envelope.issued_timestamp.to_bytes(8, "big")[4:8]
    signed_data = (
        timestamp_bytes
        + bytes([version & 0xFF])
        + blocks[0]
        + blocks[3]
        + blocks[4]
        + blocks[5]
        + blocks[6]
    )

    warnings: list[str] = []
    fields_raw = ""
    try:
        fields_raw = _decode_fields(blocks[6], version)
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"falha ao decodificar campos (v{version}): {exc}")

    field_values = fields_raw.split("^") if "^" in fields_raw else (
        [fields_raw] if fields_raw else []
    )

    return RawPayload(
        template_id=template_id,
        signed_data=signed_data,
        signature=signature,
        fields_raw=fields_raw,
        field_values=field_values,
        extra=blocks[7] or None,
        warnings=warnings,
    )


@register_format(4, "multibloco-7bit")
def parse_v4(envelope: Envelope) -> RawPayload:
    return _parse(envelope, 4)


@register_format(5, "multibloco-6bit")
def parse_v5(envelope: Envelope) -> RawPayload:
    return _parse(envelope, 5)


@register_format(6, "multibloco-base91")
def parse_v6(envelope: Envelope) -> RawPayload:
    return _parse(envelope, 6)
