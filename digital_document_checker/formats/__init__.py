"""Parsers de envelope e de formato (por versão).

O byte de versão do envelope seleciona o parser de formato:

======  ===========================  ==============================
versão  classe no APK                formato
======  ===========================  ==============================
1       ``j2.b``                     texto ``versao-b91-b91\\assinatura``
2       ``j.C0659F``                 CNH (6 bits + foto BPG)
3       ``y1.d``                     DNI/TSE (basE91 + foto nativa)
4       ``y1.f``                     multibloco (7 bits)
5       ``y1.h``                     multibloco (6 bits)
6       ``y1.j``                     multibloco (basE91 + 7 bits)
======  ===========================  ==============================
"""

from .envelope import parse_envelope
from .base import Format, get_format, register_format, supported_versions
from . import v2_cnh, multiblock, v1_text  # noqa: F401  (registram-se ao importar

__all__ = [
    "parse_envelope",
    "Format",
    "get_format",
    "register_format",
    "supported_versions",
]
