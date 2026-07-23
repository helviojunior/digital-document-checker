"""Formato da versão 3 — usado pelo DNI/TSE (classe ``y1.d`` no APK).

Layout do payload (após o cabeçalho de 10 bytes)::

    [0:2]                  template_id (big-endian)
    [2:258]               assinatura digital (256 bytes)
    [258:260]             len1 (tamanho do bloco da foto, big-endian)
    [260:260+len1]        foto BPG (sem o magic "BPG")
    [260+len1:262+len1]   len2 (tamanho dos campos, big-endian)
    [262+len1:...]        campos em basE91 (separados por '^')
    [...:]               extra (hash/segunda assinatura)

Dado assinado (ver ``.i()`` no APK)::

    signed = header + payload[0:2] + payload[258:260+len1]
             + payload[260+len1:262+len1+len2]

.. note::
   Parsing derivado da engenharia reversa do app; ainda **não validado contra
   amostras reais** de DNI. Marcado como experimental.
"""

from __future__ import annotations

from ..codecs import base91
from ..exceptions import ParseError
from ..models import Envelope, RawPayload
from .base import register_format

SIGNATURE_SIZE = 256
PHOTO_MAGIC = b"BPG"


@register_format(3, "DNI-base91")
def parse(envelope: Envelope) -> RawPayload:
    payload = envelope.payload
    if len(payload) < 260:
        raise ParseError("payload v3 muito curto para conter cabeçalho + assinatura")

    template_id = int.from_bytes(payload[0:2], "big")
    signature = payload[2:258]

    len1 = int.from_bytes(payload[258:260], "big")
    photo_end = 260 + len1
    if len(payload) < photo_end + 2:
        raise ParseError("payload v3 truncado no bloco da foto")
    photo_block = payload[260:photo_end]

    len2 = int.from_bytes(payload[photo_end:photo_end + 2], "big")
    fields_start = photo_end + 2
    fields_end = fields_start + len2
    if len(payload) < fields_end:
        raise ParseError("payload v3 truncado no bloco de campos")

    warnings: list[str] = []
    fields_raw = ""
    try:
        fields_raw = base91.decode(payload[fields_start:fields_end]).decode("latin-1")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"falha ao decodificar campos v3: {exc}")

    extra = payload[fields_end:] or None
    photo = (PHOTO_MAGIC + photo_block) if photo_block else None

    signed_data = (
        envelope.raw
        + payload[0:2]
        + payload[258:photo_end]
        + payload[photo_end:fields_end]
    )

    field_values = fields_raw.split("^") if fields_raw else []

    return RawPayload(
        template_id=template_id,
        signed_data=signed_data,
        signature=signature,
        fields_raw=fields_raw,
        field_values=field_values,
        photo=photo,
        extra=extra,
        warnings=warnings,
    )
