"""Codecs de texto usados nos QRCodes de documentos digitais.

Dois alfabetos empacotados em bits são utilizados pelos envelopes:

* **6 bits** (versões 2 e 5) — alfabeto ASCII 32..95 (``v2.o0`` no APK).
* **7 bits** (versão 4) — alfabeto de 126 símbolos com acentuação (``L1.b``).
"""

from __future__ import annotations

from ..exceptions import DecodeError
from .bits import BitReader, BitWriter

ALPHABET_6BIT = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_"

ALPHABET_7BIT = (
    " ABCÇDEFGHIJKLMNOPQRSTUVWXYZabcçdefghijklmnopqrstuvwxyz0123456789"
    "áàéíóúüñÁÀÉÍÓÚÜÑÃãÂâÔôÕõ=+-/\\*_|()[]{}<>#%&@'\".:;,!?$\n~^êÊºª§"
)

_INDEX_6BIT = {ch: i for i, ch in enumerate(ALPHABET_6BIT)}
_INDEX_7BIT = {ch: i for i, ch in enumerate(ALPHABET_7BIT)}


def decode_6bit(data: bytes) -> str:
    """Decodifica um fluxo empacotado de 6 bits por símbolo."""
    reader = BitReader(data)
    out = []
    while reader.remaining_bits >= 6:
        out.append(ALPHABET_6BIT[reader.read_symbol(6)])
    return "".join(out)


def encode_6bit(text: str) -> bytes:
    writer = BitWriter()
    for ch in text:
        try:
            writer.write_symbol(_INDEX_6BIT[ch], 6)
        except KeyError:
            raise DecodeError(f"caractere fora do alfabeto de 6 bits: {ch!r}") from None
    return writer.getvalue()


def decode_7bit(data: bytes) -> str:
    """Decodifica um fluxo empacotado de 7 bits por símbolo."""
    reader = BitReader(data)
    out = []
    limit = len(ALPHABET_7BIT)
    while reader.remaining_bits >= 7:
        value = reader.read_symbol(7)
        if value < 0 or value >= limit:
            raise DecodeError(f"símbolo {value} não existe no alfabeto de 7 bits")
        out.append(ALPHABET_7BIT[value])
    return "".join(out)


def encode_7bit(text: str) -> bytes:
    writer = BitWriter()
    for ch in text:
        try:
            writer.write_symbol(_INDEX_7BIT[ch], 7)
        except KeyError:
            raise DecodeError(f"caractere fora do alfabeto de 7 bits: {ch!r}") from None
    return writer.getvalue()
