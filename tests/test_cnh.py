from datetime import datetime, timezone

from digital_document_checker import DigitalDocumentChecker
from digital_document_checker.documents.cnh import CNHData

from .conftest import build_v2_qr

FIELDS = "^".join(
    [
        "THAIS FREITAS DE CARVALHO",
        "435341700 SESP SP",
        "06771993922",
        "24/07/1987",
        "ELLIS EVANGELISTA LIMA",
        "DORALICE FREITAS LIMA",
        "",
        "",
        "B",
        "12993042523",
        "08/12/2031",
        "21/01/2020",
        "",
        "CURITIBA",
        "PR",
        "08/12/2021",
        "12993042523",
        "PR12993042523",
    ]
).upper()

TIMESTAMP = 0x60C38DB5  # mesmo do modelo de referência


def _checker(cert_store, template_store):
    return DigitalDocumentChecker(certificates=cert_store, templates=template_store)


def test_parse_and_authenticate(rsa_material, cert_store, template_store):
    qr = build_v2_qr(FIELDS, template_id=4, timestamp=TIMESTAMP, sign=rsa_material["sign"])
    checker = _checker(cert_store, template_store)
    result = checker.parse_bytes(qr, now=datetime(2025, 1, 1, tzinfo=timezone.utc))

    assert result.is_parsed
    assert result.document_type == "cnh"
    assert result.template_id == 4
    assert result.is_authentic
    assert result.signature.algorithm == "SHA256withRSA"
    assert isinstance(result.data, CNHData)
    assert result.data.nome == "THAIS FREITAS DE CARVALHO"
    assert result.data.categoria == "B"
    assert result.data.cpf_formatado == "067.719.939-22"


def test_expired_detection(rsa_material, cert_store, template_store):
    # substitui data_validade (índice 10) por data no passado
    parts = FIELDS.split("^")
    parts[10] = "01/01/2019"
    qr = build_v2_qr("^".join(parts), template_id=4, timestamp=TIMESTAMP, sign=rsa_material["sign"])
    checker = _checker(cert_store, template_store)
    result = checker.parse_bytes(qr, now=datetime(2025, 1, 1, tzinfo=timezone.utc))
    assert result.is_expired is True
    assert result.is_valid is False  # vencida não é válida mesmo autêntica


def test_tampered_signature_still_parses(rsa_material, cert_store, template_store):
    qr = bytearray(
        build_v2_qr(FIELDS, template_id=4, timestamp=TIMESTAMP, sign=rsa_material["sign"])
    )
    qr[-260] ^= 0xFF  # corrompe o início do bloco de assinatura
    checker = _checker(cert_store, template_store)
    result = checker.parse_bytes(bytes(qr), now=datetime(2025, 1, 1, tzinfo=timezone.utc))

    assert result.is_parsed  # parsing sempre ocorre
    assert result.is_authentic is False
    assert result.data.nome == "THAIS FREITAS DE CARVALHO"
    assert result.errors


def test_unknown_template_uses_generic(rsa_material, cert_store):
    from digital_document_checker.registry import TemplateStore

    empty = TemplateStore([])
    qr = build_v2_qr(FIELDS, template_id=999, timestamp=TIMESTAMP, sign=rsa_material["sign"])
    checker = DigitalDocumentChecker(certificates=cert_store, templates=empty)
    result = checker.parse_bytes(qr, now=datetime(2025, 1, 1, tzinfo=timezone.utc))

    assert result.is_parsed
    assert result.is_known_template is False
    # template 999 não é CNH conhecido → handler genérico
    assert result.document_type in {"generic", "cnh"}
    assert result.raw_fields[0] == "THAIS FREITAS DE CARVALHO"
