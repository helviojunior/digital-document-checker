"""basE91 com o alfabeto utilizado pelos documentos digitais (classe ``L1.a``).

O alfabeto não é o da implementação de referência do basE91: os símbolos
foram reordenados para caber no modo alfanumérico/byte do QRCode.
"""

from __future__ import annotations

ALPHABET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    "!#$%&()*+,./:;<=>?@[]^_`{|}~\""
)

_DECODE_TABLE = {ord(ch): idx for idx, ch in enumerate(ALPHABET)}
_BASE = len(ALPHABET)  # 91


def decode(data: bytes | str) -> bytes:
    """Decodifica bytes/str basE91 para os bytes originais."""
    if isinstance(data, str):
        data = data.encode("latin-1")

    out = bytearray()
    accum = 0
    n_bits = 0
    pending = -1

    for byte in data:
        value = _DECODE_TABLE.get(byte, -1)
        if value == -1:
            continue  # caracteres fora do alfabeto são ignorados
        if pending == -1:
            pending = value
            continue
        combined = value * _BASE + pending
        accum |= combined << n_bits
        n_bits += 13 if (combined & 8191) > 88 else 14
        while True:
            out.append(accum & 0xFF)
            accum >>= 8
            n_bits -= 8
            if n_bits <= 7:
                break
        pending = -1

    if pending != -1:
        out.append((pending << n_bits | accum) & 0xFF)

    return bytes(out)


def encode(data: bytes) -> str:
    """Codifica bytes em basE91 (inverso de :func:`decode`)."""
    out = []
    accum = 0
    n_bits = 0

    for byte in data:
        accum |= byte << n_bits
        n_bits += 8
        if n_bits > 13:
            value = accum & 8191
            if value > 88:
                accum >>= 13
                n_bits -= 13
            else:
                value = accum & 16383
                accum >>= 14
                n_bits -= 14
            out.append(ALPHABET[value % _BASE])
            out.append(ALPHABET[value // _BASE])

    if n_bits:
        out.append(ALPHABET[accum % _BASE])
        if n_bits > 7 or accum > 90:
            out.append(ALPHABET[accum // _BASE])

    return "".join(out)
