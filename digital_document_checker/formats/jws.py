"""Parsing de JWS compacto (RFC 7515) — formato do QRCode da CIN.

O QRCode impresso no verso da Carteira de Identidade Nacional não usa o
envelope binário do padrão VIO/SERPRO: seu conteúdo é um **JWT assinado**
(``header.payload.signature``, tudo em base64url).

O app oficial (``identidade-nacional`` 1.19.0) trata o conteúdo lido pela
câmera como string e o repassa a ``IoReactNativeJwtModule.verify``, que exige
exatamente três segmentos (``JOSEObject.split``).
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from typing import Any

from ..exceptions import ParseError

#: Três segmentos base64url separados por ponto (o último pode ser vazio: ``alg=none``).
_COMPACT_JWS_RE = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*$")


def b64url_decode(segment: str) -> bytes:
    """Decodifica um segmento base64url sem padding."""
    padding = "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(segment + padding)
    except Exception as exc:  # noqa: BLE001
        raise ParseError(f"segmento base64url inválido: {exc}") from exc


def as_text(data: bytes | str) -> str | None:
    """Converte os bytes do QRCode em texto ASCII, quando possível."""
    if isinstance(data, str):
        return data
    try:
        return data.decode("ascii")
    except (UnicodeDecodeError, AttributeError):
        return None


def looks_like_compact_jws(data: bytes | str) -> bool:
    """Indica se o conteúdo do QRCode tem a cara de um JWT compacto."""
    text = as_text(data)
    if text is None:
        return False
    return bool(_COMPACT_JWS_RE.match(text.strip()))


@dataclass
class CompactJWS:
    """JWS compacto já dividido e decodificado."""

    raw: str
    header: dict[str, Any] = field(default_factory=dict)
    claims: dict[str, Any] = field(default_factory=dict)
    signature: bytes = b""
    #: ``ASCII(BASE64URL(header) || '.' || BASE64URL(payload))`` — o dado assinado.
    signing_input: bytes = b""

    @property
    def algorithm(self) -> str | None:
        return self.header.get("alg")

    @property
    def key_id(self) -> str | None:
        return self.header.get("kid")


def parse_compact_jws(data: bytes | str) -> CompactJWS:
    """Divide e decodifica um JWS compacto.

    Levanta :class:`ParseError` quando o conteúdo não tem três segmentos ou
    quando o *payload* não é um objeto JSON.
    """
    text = as_text(data)
    if text is None:
        raise ParseError("conteúdo do QRCode não é texto ASCII")
    text = text.strip()

    parts = text.split(".")
    if len(parts) != 3:
        raise ParseError(
            f"esperados 3 segmentos no JWS compacto, encontrados {len(parts)}"
        )

    header_b64, payload_b64, signature_b64 = parts
    if not header_b64 or not payload_b64:
        raise ParseError("cabeçalho ou payload vazios")

    try:
        header = json.loads(b64url_decode(header_b64))
    except json.JSONDecodeError as exc:
        raise ParseError(f"cabeçalho JOSE não é JSON: {exc}") from exc
    if not isinstance(header, dict):
        raise ParseError("cabeçalho JOSE não é um objeto")

    try:
        claims = json.loads(b64url_decode(payload_b64))
    except json.JSONDecodeError as exc:
        raise ParseError(f"payload não é JSON: {exc}") from exc
    if not isinstance(claims, dict):
        raise ParseError("payload do JWT não é um objeto")

    return CompactJWS(
        raw=text,
        header=header,
        claims=claims,
        signature=b64url_decode(signature_b64) if signature_b64 else b"",
        signing_input=f"{header_b64}.{payload_b64}".encode("ascii"),
    )
