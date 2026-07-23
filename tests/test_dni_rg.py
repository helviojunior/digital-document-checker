from datetime import datetime, timezone

from digital_document_checker import DigitalDocumentChecker
from digital_document_checker.documents.dni import DNIData
from digital_document_checker.documents.rg import RGData
from digital_document_checker.registry import TemplateStore

from .conftest import build_v3_qr

TIMESTAMP = 0x60C38DB5


def _template_store():
    def fields(names):
        return [{"name": n} for n in names]

    return TemplateStore.from_json(
        [
            {
                "id": 8,
                "name": "DNI",
                "owner": {"id": 2, "name": "TSE"},
                "fields": fields(
                    [
                        "numero_icn",
                        "nome",
                        "matricula_nascimento",
                        "data_nascimento",
                        "filiacao_1",
                        "filiacao_2",
                        "naturalidade",
                        "cpf",
                        "titulo_eleitor",
                        "orgao_expedidor",
                        "data_expedicao",
                        "situacao_registro",
                        "data_ultima_atualizacao",
                    ]
                ),
                "certificate_group": {"id": "test-group"},
            },
            {
                "id": 91,
                "name": "RG Digital",
                "owner": {"id": 3, "name": "GovBr"},
                "fields": fields(
                    [
                        "nome",
                        "nome_social",
                        "cpf",
                        "sexo",
                        "data_nascimento",
                        "nacionalidade",
                        "naturalidade",
                        "data_validade",
                        "filiacao_1",
                        "filiacao_2",
                        "orgao_expedidor",
                        "local_emissao",
                        "data_emissao",
                        "certidao",
                        "hash",
                    ]
                ),
                "certificate_group": {"id": "test-group"},
            },
        ]
    )


DNI_FIELDS = "^".join(
    [
        "123456789",
        "MARIA SOUZA LIMA",
        "0987654",
        "10/05/1990",
        "JOSE SOUZA",
        "ANA LIMA",
        "FORTALEZA",
        "01234567890",
        "1234 5678 9012",
        "TSE",
        "01/02/2020",
        "REGULAR",
        "01/02/2020",
    ]
)

RG_FIELDS = "^".join(
    [
        "CARLOS PEREIRA",
        "",
        "01234567890",
        "M",
        "15/03/1985",
        "BRASILEIRA",
        "SAO PAULO-SP",
        "15/03/2035",
        "PEDRO PEREIRA",
        "JULIA PEREIRA",
        "SSP-SP",
        "SAO PAULO",
        "20/01/2023",
        "certidao-x",
        "abc123hash",
    ]
)


def test_dni_v3_parse_and_authenticate(rsa_material, cert_store):
    qr = build_v3_qr(
        DNI_FIELDS,
        template_id=8,
        timestamp=TIMESTAMP,
        sign=rsa_material["sign"],
        photo=b"\x00\x01\x02\x03",  # bloco de foto fictício
    )
    checker = DigitalDocumentChecker(certificates=cert_store, templates=_template_store())
    result = checker.parse_bytes(qr, now=datetime(2025, 1, 1, tzinfo=timezone.utc))

    assert result.is_parsed
    assert result.qr_version == 3
    assert result.document_type == "dni"
    assert result.is_authentic
    assert isinstance(result.data, DNIData)
    assert result.data.nome == "MARIA SOUZA LIMA"
    assert result.data.cpf_formatado == "012.345.678-90"
    assert result.data.filiacao == ["JOSE SOUZA", "ANA LIMA"]
    # a foto vem com o magic BPG reconstruído
    assert result.photo is not None
    assert result.photo.data.startswith(b"BPG")


def test_dni_tampered_still_parses(rsa_material, cert_store):
    qr = bytearray(
        build_v3_qr(DNI_FIELDS, template_id=8, timestamp=TIMESTAMP, sign=rsa_material["sign"])
    )
    # assinatura = qr[12:268] (header 10 + template_id 2); corrompe no meio dela
    qr[130] ^= 0xFF
    checker = DigitalDocumentChecker(certificates=cert_store, templates=_template_store())
    result = checker.parse_bytes(bytes(qr), now=datetime(2025, 1, 1, tzinfo=timezone.utc))
    assert result.is_parsed
    assert result.is_authentic is False
    assert result.data.nome == "MARIA SOUZA LIMA"


def test_rg_digital_routing_and_expiry(rsa_material, cert_store):
    # RGHandler roteia por template_id (independe da versão de envelope);
    # usa envelope v3 (basE91) por preservar minúsculas/acentos.
    qr = build_v3_qr(RG_FIELDS, template_id=91, timestamp=TIMESTAMP, sign=rsa_material["sign"])
    checker = DigitalDocumentChecker(certificates=cert_store, templates=_template_store())
    result = checker.parse_bytes(qr, now=datetime(2025, 1, 1, tzinfo=timezone.utc))

    assert result.is_parsed
    assert result.document_type == "rg_digital"
    assert result.is_authentic
    assert isinstance(result.data, RGData)
    assert result.data.nome == "CARLOS PEREIRA"
    assert result.data.orgao_expedidor == "SSP-SP"
    assert result.is_expired is False  # validade 2035
    assert result.is_valid is True


def test_rg_digital_expired(rsa_material, cert_store):
    parts = RG_FIELDS.split("^")
    parts[7] = "01/01/2020"  # data_validade no passado
    qr = build_v3_qr("^".join(parts), template_id=91, timestamp=TIMESTAMP, sign=rsa_material["sign"])
    checker = DigitalDocumentChecker(certificates=cert_store, templates=_template_store())
    result = checker.parse_bytes(qr, now=datetime(2025, 1, 1, tzinfo=timezone.utc))
    assert result.is_expired is True
    assert result.is_valid is False
