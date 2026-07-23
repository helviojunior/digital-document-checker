import base64

import pytest

from digital_document_checker.codecs import base91
from digital_document_checker.codecs.text import encode_6bit
from digital_document_checker.models import Certificate
from digital_document_checker.registry import CertificateStore, TemplateStore


def build_v2_qr(fields_text: str, *, template_id: int, timestamp: int, sign) -> bytes:
    """Monta um QRCode v2 (CNH) e assina o dado reconstruído."""
    header = f"{timestamp:08x}{2:02x}".encode("latin-1")  # versão 2
    encoded_fields = encode_6bit(fields_text)
    prefix = template_id.to_bytes(2, "big") + len(encoded_fields).to_bytes(2, "big")
    signed_prefix = header + prefix + encoded_fields  # header + payload[0:i9]
    signature = sign(signed_prefix)  # 256 bytes (RSA)
    payload = prefix + encoded_fields + signature
    return header + payload


def build_v3_qr(
    fields_text: str,
    *,
    template_id: int,
    timestamp: int,
    sign,
    photo: bytes = b"",
    extra: bytes = b"",
) -> bytes:
    """Monta um QRCode v3 (DNI) e assina o dado reconstruído."""
    header = f"{timestamp:08x}{3:02x}".encode("latin-1")  # versão 3
    tid = template_id.to_bytes(2, "big")
    fields_b91 = base91.encode(fields_text.encode("latin-1")).encode("latin-1")

    len1 = len(photo).to_bytes(2, "big")
    len2 = len(fields_b91).to_bytes(2, "big")

    # signed = header + tid + (len1 + photo) + (len2 + fields_b91)
    signed = header + tid + len1 + photo + len2 + fields_b91
    signature = sign(signed)  # 256 bytes

    payload = tid + signature + len1 + photo + len2 + fields_b91 + extra
    return header + payload


@pytest.fixture
def rsa_material():
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pub_der = key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    pub_b64 = base64.b64encode(pub_der).decode()

    def sign(data: bytes) -> bytes:
        return key.sign(data, padding.PKCS1v15(), hashes.SHA256())

    return {"sign": sign, "public_key_b64": pub_b64}


@pytest.fixture
def cert_store(rsa_material):
    from datetime import datetime, timezone

    cert = Certificate(
        id="test-cert",
        group_id="test-group",
        public_key_b64=rsa_material["public_key_b64"],
        valid_from=datetime(2000, 1, 1, tzinfo=timezone.utc),
        valid_until=datetime(2100, 1, 1, tzinfo=timezone.utc),
    )
    return CertificateStore([cert])


@pytest.fixture
def template_store():
    payload = [
        {
            "id": 4,
            "name": "CNH",
            "owner": {"id": 1, "name": "SENATRAN"},
            "fields": [
                {"name": n}
                for n in [
                    "nome",
                    "identidade",
                    "cpf",
                    "data_nascimento",
                    "filiacao_pai",
                    "filiacao_mae",
                    "permissao",
                    "acc",
                    "categoria",
                    "numero_registro",
                    "data_validade",
                    "data_primeira_habilitacao",
                    "observacoes",
                    "local_emissao",
                    "uf_emissao",
                    "data_emissao",
                    "numero_validacao_cnh",
                    "numero_renach",
                ]
            ],
            "certificate_group": {"id": "test-group"},
            "sandbox": False,
        }
    ]
    return TemplateStore.from_json(payload)
