"""Verificação da assinatura digital.

Dois caminhos, conforme o documento:

* **VIO/SERPRO** (CNH, DNI, RG Digital) — ``SHA256withRSA`` /
  ``SHA256withECDSA`` sobre o dado assinado do envelope binário. Reproduz
  ``v2.R4`` do APK: a escolha do algoritmo depende do tamanho da chave e da
  assinatura. Assinaturas RSA têm 256 bytes; abaixo disso o app tenta ECDSA.
* **CIN** (Carteira de Identidade Nacional) — JWS ``ES256``/``ES384``/``ES512``
  com a chave pública em formato JWK. Reproduz
  ``IoReactNativeJwtModule.verify``, que usa o ``ECDSAVerifier`` do Nimbus: a
  assinatura vem no formato JOSE (``R || S`` de tamanho fixo), e não em DER.
"""

from __future__ import annotations

import base64
from typing import Any, Optional

try:  # dependência preferencial
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, padding
    from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePublicKey
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
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


# --------------------------------------------------------------------------- #
# JWS (CIN)
# --------------------------------------------------------------------------- #
#: ``alg`` do JOSE → (nome da curva no JWK, curva, hash, tamanho de R e S).
_JWS_EC_ALGORITHMS: dict[str, tuple[str, Any, Any, int]] = {}
if _HAS_CRYPTOGRAPHY:  # pragma: no branch - depende só do import
    _JWS_EC_ALGORITHMS = {
        "ES256": ("P-256", ec.SECP256R1, hashes.SHA256, 32),
        "ES384": ("P-384", ec.SECP384R1, hashes.SHA384, 48),
        "ES512": ("P-521", ec.SECP521R1, hashes.SHA512, 66),
    }


def _b64url_to_int(value: str) -> int:
    padding_len = "=" * (-len(value) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(value + padding_len), "big")


def load_ec_jwk(jwk: dict) -> "EllipticCurvePublicKey":
    """Constrói uma chave pública EC a partir de um JWK (``kty`` = ``EC``)."""
    if not _HAS_CRYPTOGRAPHY:
        raise RuntimeError("dependência 'cryptography' não instalada")
    if jwk.get("kty") != "EC":
        raise ValueError(f"JWK não é EC: kty={jwk.get('kty')!r}")

    curve_name = jwk.get("crv")
    curve = next(
        (c for (name, c, _h, _s) in _JWS_EC_ALGORITHMS.values() if name == curve_name),
        None,
    )
    if curve is None:
        raise ValueError(f"curva não suportada: {curve_name!r}")

    numbers = ec.EllipticCurvePublicNumbers(
        _b64url_to_int(jwk["x"]), _b64url_to_int(jwk["y"]), curve()
    )
    return numbers.public_key()


def verify_jws(
    signing_input: bytes, signature: bytes, jwk: dict, algorithm: Optional[str]
) -> tuple[bool, Optional[str]]:
    """Verifica a assinatura de um JWS compacto com uma chave pública JWK.

    Retorna ``(is_authentic, algorithm_or_reason)``, no mesmo contrato de
    :func:`verify`.
    """
    if not _HAS_CRYPTOGRAPHY:
        return False, "dependência 'cryptography' não instalada"
    if not algorithm:
        return False, "cabeçalho JOSE sem 'alg'"

    spec = _JWS_EC_ALGORITHMS.get(algorithm)
    if spec is None:
        return False, f"algoritmo JWS não suportado: {algorithm}"
    curve_name, _curve, hash_cls, coordinate_len = spec

    if jwk.get("crv") != curve_name:
        return False, f"alg {algorithm} incompatível com a curva {jwk.get('crv')!r}"
    if len(signature) != coordinate_len * 2:
        return False, (
            f"assinatura com {len(signature)} bytes; "
            f"esperados {coordinate_len * 2} para {algorithm}"
        )

    try:
        public_key = load_ec_jwk(jwk)
    except Exception as exc:  # noqa: BLE001
        return False, f"falha ao carregar a chave pública: {exc}"

    # Nimbus/JOSE transmitem R||S concatenados; o cryptography espera DER.
    r = int.from_bytes(signature[:coordinate_len], "big")
    s = int.from_bytes(signature[coordinate_len:], "big")
    der_signature = encode_dss_signature(r, s)

    try:
        public_key.verify(der_signature, signing_input, ec.ECDSA(hash_cls()))
    except InvalidSignature:
        return False, algorithm
    except Exception as exc:  # noqa: BLE001
        return False, f"erro ao verificar ({algorithm}): {exc}"

    return True, algorithm
