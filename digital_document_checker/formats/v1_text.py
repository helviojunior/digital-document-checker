"""Formato da versão 1 (classe ``j2.b`` no APK).

O payload é interpretado como texto no formato::

    <versao>-<campos_base91>-<extra_base91>\\<assinatura_base91>

.. note::
   Formato legado; parsing estrutural implementado, ainda não validado contra
   amostras reais.
"""

from __future__ import annotations

from ..codecs import base91
from ..exceptions import ParseError
from ..models import Envelope, RawPayload
from .base import register_format


@register_format(1, "texto-base91")
def parse(envelope: Envelope) -> RawPayload:
    try:
        text = envelope.payload.decode("latin-1")
    except UnicodeDecodeError as exc:  # pragma: no cover
        raise ParseError(f"payload v1 não é texto latin-1: {exc}") from None

    if "\\" not in text:
        raise ParseError("payload v1 sem separador de assinatura")

    data_part, _, signature_part = text.partition("\\")
    signature = base91.decode(signature_part) if signature_part else b""

    segments = data_part.split("-", 2)
    if len(segments) != 3:
        raise ParseError("payload v1 com número inesperado de segmentos")

    version_hex, fields_b91, extra_b91 = segments
    warnings: list[str] = []

    fields_raw = ""
    if fields_b91:
        try:
            fields_raw = base91.decode(fields_b91).decode("latin-1")
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"falha ao decodificar campos v1: {exc}")

    extra = base91.decode(extra_b91) if extra_b91 else None

    # template_id não é transportado explicitamente neste formato
    field_values = fields_raw.split("¬") if fields_raw else []

    return RawPayload(
        template_id=-1,
        signed_data=envelope.raw + envelope.payload,  # aproximação
        signature=signature,
        fields_raw=fields_raw,
        field_values=field_values,
        extra=extra,
        warnings=warnings + ["formato v1: template_id ausente no payload"],
    )
