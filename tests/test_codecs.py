import random

import pytest

from digital_document_checker.codecs import base91
from digital_document_checker.codecs.bits import BitReader, BitWriter
from digital_document_checker.codecs.text import (
    decode_6bit,
    decode_7bit,
    encode_6bit,
    encode_7bit,
)


def test_bit_roundtrip_symbols():
    writer = BitWriter()
    values = [(5, 6), (63, 6), (0, 6), (42, 6)]
    for value, bits in values:
        writer.write_symbol(value, bits)
    reader = BitReader(writer.getvalue())
    for value, bits in values:
        assert reader.read_symbol(bits) == value


def test_6bit_roundtrip():
    text = "THAIS FREITAS^06771993922^CURITIBA^PR"
    encoded = encode_6bit(text)
    assert decode_6bit(encoded).startswith(text)


def test_6bit_alphabet_only():
    # apenas caracteres do alfabeto de 6 bits são aceitos
    with pytest.raises(Exception):
        encode_6bit("ação")  # 'ç' e 'ã' não estão no alfabeto


def test_7bit_roundtrip():
    text = "JOÃO DA SILVA"
    encoded = encode_7bit(text)
    assert decode_7bit(encoded).startswith(text)


def test_base91_roundtrip():
    random.seed(7)
    for _ in range(200):
        data = bytes(random.randrange(256) for _ in range(random.randint(0, 64)))
        assert base91.decode(base91.encode(data)) == data
