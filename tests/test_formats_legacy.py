"""Formatos v1 e multibloco (v4/v5/v6), conforme o app VIO 2.4.5."""

from datetime import datetime, timezone

import pytest

from digital_document_checker import DigitalDocumentChecker
from digital_document_checker.registry import TemplateStore

from .conftest import build_multiblock_qr, build_v1_qr

TIMESTAMP = 0x60C38DB5
NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)

# v1 separa os campos por "¬"; as demais versões por "^".
V1_FIELDS = "¬".join(["JOAO DA SILVA", "01234567890", "10/05/1990"])
MB_FIELDS = "^".join(["JOAO DA SILVA", "01234567890", "10/05/1990"])


def _template_store(template_id: int) -> TemplateStore:
    return TemplateStore.from_json(
        [
            {
                "id": template_id,
                "name": "Documento Digital",
                "owner": {"id": 1, "name": "SERPRO"},
                "fields": [
                    {"name": n} for n in ("nome", "cpf", "data_nascimento")
                ],
                "certificate_group": {"id": "test-group"},
            }
        ]
    )


def test_v1_parse_and_authenticate(rsa_material, cert_store):
    qr = build_v1_qr(
        V1_FIELDS,
        template_id=0x2A,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
        image=b"\x89PNG\r\n\x1a\n-fake",
    )
    checker = DigitalDocumentChecker(
        certificates=cert_store, templates=_template_store(0x2A)
    )
    result = checker.parse_bytes(qr, now=NOW)

    assert result.is_parsed
    assert result.qr_version == 1
    # o template_id vem do primeiro segmento, em hexadecimal
    assert result.template_id == 0x2A
    assert result.is_known_template
    assert result.raw_fields == ["JOAO DA SILVA", "01234567890", "10/05/1990"]
    # a assinatura confere com o dado reconstruído pelo app
    assert result.is_authentic
    # no v1 a imagem já traz o próprio cabeçalho (sem magic BPG postiço)
    assert result.photo is not None
    assert result.photo.format == "PNG"


@pytest.mark.parametrize("version", [4, 5, 6])
def test_multiblock_parse_and_authenticate(version, rsa_material, cert_store):
    qr = build_multiblock_qr(
        MB_FIELDS,
        version=version,
        template_id=77,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
        photo=b"\x00\x01\x02\x03",
        extra=b"\xaa\xbb",
    )
    checker = DigitalDocumentChecker(
        certificates=cert_store, templates=_template_store(77)
    )
    result = checker.parse_bytes(qr, now=NOW)

    assert result.is_parsed
    assert result.qr_version == version
    assert result.template_id == 77
    assert result.is_authentic
    assert result.raw_fields == ["JOAO DA SILVA", "01234567890", "10/05/1990"]
    # blocks[4] é a foto BPG, gravada sem o magic
    assert result.photo is not None
    assert result.photo.data == b"BPG\x00\x01\x02\x03"
    assert result.photo.format == "BPG"
    assert result.extra == b"\xaa\xbb"


def test_v6_fields_are_base91_only(rsa_material, cert_store):
    """Regressão: o v6 é basE91 puro, sem desempacotamento de 7 bits."""
    qr = build_multiblock_qr(
        MB_FIELDS,
        version=6,
        template_id=77,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
    )
    checker = DigitalDocumentChecker(
        certificates=cert_store, templates=_template_store(77)
    )
    result = checker.parse_bytes(qr, now=NOW)

    assert result.fields_raw_string == MB_FIELDS
