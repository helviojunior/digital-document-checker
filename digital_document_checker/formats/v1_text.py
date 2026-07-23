"""Formato da versão 1 (classe ``m8.c`` no APK).

O payload é interpretado como texto ISO-8859-1 no formato::

    <template_id_hex>-<campos_base91>-<imagem_base91>\\<assinatura_base91>

O ``template_id`` é o primeiro segmento lido como hexadecimal
(``Long.decode("0x" + seg0)`` no APK). O terceiro segmento é a imagem, que
neste formato já carrega o próprio cabeçalho — não recebe o magic ``BPG``.

Dado assinado (ver ``.x()`` no APK)::

    signed = header10 + seg0 + "-" + campos_decodificados + "-"   (ISO-8859-1)
             + basE91(seg2)

.. note::
   Formato legado; parsing derivado da engenharia reversa do app, ainda não
   validado contra amostras reais.
"""

from __future__ import annotations

from ..codecs import base91
from ..exceptions import ParseError
from ..models import Envelope, RawPayload
from .base import register_format

FIELD_SEPARATOR = "¬"


@register_format(1, "texto-base91")
def parse(envelope: Envelope) -> RawPayload:
    try:
        text = envelope.payload.decode("latin-1")
    except UnicodeDecodeError as exc:  # pragma: no cover
        raise ParseError(f"payload v1 não é texto ISO-8859-1: {exc}") from None

    # O app exige exatamente duas partes: dados e assinatura.
    parts = text.split("\\")
    if len(parts) != 2:
        raise ParseError("payload v1 sem separador de assinatura")

    data_part, signature_part = parts
    signature = base91.decode(signature_part) if signature_part else b""

    segments = data_part.split("-")
    if len(segments) != 3:
        raise ParseError("payload v1 com número inesperado de segmentos")

    template_hex, fields_b91, image_b91 = segments

    try:
        template_id = int(template_hex, 16)
    except ValueError:
        raise ParseError(f"template_id v1 inválido: {template_hex!r}") from None

    warnings: list[str] = []

    fields_raw = ""
    if fields_b91:
        try:
            fields_raw = base91.decode(fields_b91).decode("latin-1")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"falha ao decodificar campos v1: {exc}")

    photo = base91.decode(image_b91) if image_b91 else None

    # signed = header + seg0 + "-" + campos + "-" em ISO-8859-1, seguido dos
    # bytes crus da imagem.
    signed_data = (
        envelope.signed_header
        + f"{template_hex}-{fields_raw}-".encode("latin-1")
        + (photo or b"")
    )

    field_values = fields_raw.split(FIELD_SEPARATOR) if fields_raw else []

    return RawPayload(
        template_id=template_id,
        signed_data=signed_data,
        signature=signature,
        fields_raw=fields_raw,
        field_values=field_values,
        photo=photo,
        warnings=warnings,
    )
