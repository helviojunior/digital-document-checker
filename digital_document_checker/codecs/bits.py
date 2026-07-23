"""Leitor/escritor de bits MSB-first.

Porte fiel do ``BitReader`` usado pelo aplicativo VIO (classe ``u1.e`` /
``v2.o0`` no APK): os bits são lidos do mais significativo para o menos
significativo e o último byte parcial é gravado **sem padding à esquerda**.
"""

from __future__ import annotations


class BitReader:
    """Lê grupos de N bits de um buffer, em ordem MSB-first."""

    __slots__ = ("_data", "_bit_pos")

    def __init__(self, data: bytes) -> None:
        if data is None:
            raise ValueError("data não pode ser None")
        self._data = bytes(data)
        self._bit_pos = 0

    @property
    def remaining_bits(self) -> int:
        return len(self._data) * 8 - self._bit_pos

    def read_bits(self, n_bits: int) -> bytes:
        if n_bits < 0:
            raise ValueError("n_bits deve ser não-negativo")
        if n_bits == 0:
            return b""

        out = bytearray()
        collected = 0
        current = 0

        while n_bits > 0:
            if self._bit_pos >= len(self._data) * 8:
                raise EOFError("bits insuficientes no buffer")

            byte_index = self._bit_pos // 8
            bit_in_byte = self._bit_pos % 8
            available = 8 - bit_in_byte

            take = min(n_bits, min(8 - collected, available))
            shift = 8 - (bit_in_byte + take)
            val = (self._data[byte_index] >> shift) & ((1 << take) - 1)

            current = (current << take) | val
            collected += take
            self._bit_pos += take
            n_bits -= take

            if collected != 8 and n_bits == 0:
                break

            if collected == 8:
                out.append(current & 0xFF)
                current = 0
                collected = 0

        if collected > 0:
            # byte parcial gravado sem padding à esquerda (idêntico ao Java)
            out.append(current & 0xFF)

        return bytes(out)

    def read_symbol(self, n_bits: int) -> int:
        """Lê ``n_bits`` (<= 8) e devolve o valor inteiro correspondente."""
        if n_bits > 8:
            raise ValueError("read_symbol suporta no máximo 8 bits")
        return self.read_bits(n_bits)[0]


class BitWriter:
    """Escreve símbolos de N bits em ordem MSB-first (inverso do BitReader)."""

    __slots__ = ("_out", "_current", "_collected")

    def __init__(self) -> None:
        self._out = bytearray()
        self._current = 0
        self._collected = 0

    def write_symbol(self, value: int, n_bits: int) -> None:
        self._current = (self._current << n_bits) | (value & ((1 << n_bits) - 1))
        self._collected += n_bits
        while self._collected >= 8:
            self._out.append((self._current >> (self._collected - 8)) & 0xFF)
            self._collected -= 8

    def getvalue(self) -> bytes:
        if self._collected == 0:
            return bytes(self._out)
        # Alinha o byte parcial à esquerda (MSB), tornando o writer o inverso
        # exato do BitReader — que lê sempre em ordem MSB-first.
        partial = (self._current & ((1 << self._collected) - 1)) << (8 - self._collected)
        return bytes(self._out) + bytes([partial & 0xFF])
