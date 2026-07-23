"""Verificação da assinatura digital (SHA256withRSA / SHA256withECDSA).

Reproduz ``v2.R4`` do APK: a escolha do algoritmo depende do tamanho da chave
e da assinatura. Assinaturas RSA têm 256 bytes; abaixo disso o app tenta ECDSA.
"""

from __future__ import annotations

import base64
from typing import Optional

try:  # dependência preferencial
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, padding
    from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
    from cryptography.hazmat.primitives.serialization import load_der_public_key

    _HAS_CRYPTOGRAPHY = True
except ImportError:  # pragma: no cover - ambiente sem cryptography
    _HAS_CRYPTOGRAPHY = False


RSA = "SHA256withRSA"
ECDSA = "SHA256withECDSA"


def is_available() -> bool:
    return _HAS_CRYPTOGRAPHY


def select_algorithm(public_key_der: bytes, signature: bytes) -> Optional[str]:
    """Espelha a heurística de ``R4.b`` baseada no tamanho dos buffers."""
    if len(public_key_der) < 256 and len(signature) < 256:
        return ECDSA
    if len(public_key_der) >= 256 and len(signature) >= 256:
        return RSA
    return None  # combinação inconsistente → app retorna falso


def verify(data: bytes, signature: bytes, public_key_b64: str) -> tuple[bool, Optional[str]]:
    """Verifica a assinatura. Retorna ``(is_authentic, algorithm_or_reason)``.

    O segundo elemento é o nome do algoritmo usado quando a verificação ocorre,
    ou uma mensagem de erro quando ela não pôde ser realizada.
    """
    if not _HAS_CRYPTOGRAPHY:
        return False, "dependência 'cryptography' não instalada"

    try:
        public_key_der = base64.b64decode(public_key_b64)
    except Exception as exc:  # noqa: BLE001
        return False, f"chave pública inválida: {exc}"

    algorithm = select_algorithm(public_key_der, signature)
    if algorithm is None:
        return False, "tamanho de chave/assinatura incompatível"

    try:
        public_key = load_der_public_key(public_key_der)
    except Exception as exc:  # noqa: BLE001
        return False, f"falha ao carregar a chave pública: {exc}"

    try:
        if algorithm == RSA:
            if not isinstance(public_key, RSAPublicKey):
                return False, "esperada chave RSA"
            public_key.verify(signature, data, padding.PKCS1v15(), hashes.SHA256())
        else:
            if not isinstance(public_key, EllipticCurvePublicKey):
                return False, "esperada chave EC"
            public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
    except InvalidSignature:
        return False, algorithm
    except Exception as exc:  # noqa: BLE001
        return False, f"erro ao verificar ({algorithm}): {exc}"

    return True, algorithm
