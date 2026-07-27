"""Testes da CIN — Carteira de Identidade Nacional (QRCode = JWT ES512)."""

from datetime import datetime, timezone

import pytest

from digital_document_checker import DigitalDocumentChecker
from digital_document_checker.documents.cin import CINHandler
from digital_document_checker.exceptions import ParseError
from digital_document_checker.formats.jws import (
    looks_like_compact_jws,
    parse_compact_jws,
)
from digital_document_checker.registry import default_cin_keys

from .conftest import build_cin_qr


@pytest.fixture
def checker(cin_key_store):
    return DigitalDocumentChecker(cin_keys=cin_key_store)


def test_qrcode_valido(checker, cin_material, cin_claims):
    token = build_cin_qr(cin_claims, sign=cin_material["sign"])
    result = checker.parse_qr_text(token)

    assert result.is_parsed
    assert result.is_authentic
    assert result.is_valid
    assert result.document_type == "cin"
    assert result.document_name == "Carteira de Identidade Nacional"
    assert result.header_format == "jws"
    assert result.signature.algorithm == "ES512"
    assert result.signature.certificate_id == "PROD"
    assert not result.errors


def test_campos_extraidos(checker, cin_material, cin_claims):
    token = build_cin_qr(cin_claims, sign=cin_material["sign"])
    data = checker.parse_qr_text(token).data

    assert data.cpf == "12345678901"
    assert data.cpf_formatado == "123.456.789-01"
    assert data.data_nascimento == "01/01/1990"  # claim 'dns'
    assert data.iss == "MJSP"
    assert data.uuid == "8f14e45f-ceea-467a-9c0a-1e02d5a1e0f3"


def test_claims_nao_mapeadas_vao_para_extras(checker, cin_material, cin_claims):
    token = build_cin_qr({**cin_claims, "jti": "abc", "sub": "x"}, sign=cin_material["sign"])
    result = checker.parse_qr_text(token)

    assert result.data.outras_claims == {"jti": "abc", "sub": "x"}
    assert result.fields["jti"] == "abc"


def test_dvd_define_validade(checker, cin_material, cin_claims):
    """A claim 'dvd' é a validade impressa no cartão."""
    result = checker.parse_qr_text(
        build_cin_qr(cin_claims, sign=cin_material["sign"]),
        now=datetime(2026, 7, 27, tzinfo=timezone.utc),
    )

    assert result.data.data_validade == "02/02/2036"
    assert result.expires_on == datetime(2036, 2, 2, tzinfo=timezone.utc)
    assert result.is_expired is False
    assert result.is_valid


def test_dvd_no_passado_marca_vencido(checker, cin_material, cin_claims):
    token = build_cin_qr({**cin_claims, "dvd": "01/01/2020"}, sign=cin_material["sign"])
    result = checker.parse_qr_text(token, now=datetime(2026, 7, 27, tzinfo=timezone.utc))

    assert result.is_expired is True
    assert result.is_authentic  # a assinatura continua válida
    assert not result.is_valid


def test_dvd_tem_prioridade_sobre_exp(checker, cin_material, cin_claims):
    token = build_cin_qr({**cin_claims, "exp": 1000000000}, sign=cin_material["sign"])
    result = checker.parse_qr_text(token, now=datetime(2026, 7, 27, tzinfo=timezone.utc))

    assert result.expires_on == datetime(2036, 2, 2, tzinfo=timezone.utc)
    assert result.is_expired is False


def test_parse_bytes_aceita_o_token(checker, cin_material, cin_claims):
    token = build_cin_qr(cin_claims, sign=cin_material["sign"])
    assert checker.parse_bytes(token.encode("ascii")).is_authentic


def test_assinatura_adulterada(checker, cin_material, cin_claims):
    token = build_cin_qr(cin_claims, sign=cin_material["sign"])
    adulterado = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    result = checker.parse_qr_text(adulterado)

    # o parsing continua acontecendo — só a autenticidade cai
    assert result.is_parsed
    assert result.fields["cpf"] == "12345678901"
    assert not result.is_authentic
    assert not result.is_valid
    assert any("assinatura não confere" in e for e in result.errors)


def test_payload_adulterado(checker, cin_material, cin_claims):
    """Trocar o CPF invalida a assinatura, pois ela cobre header.payload."""
    token = build_cin_qr(cin_claims, sign=cin_material["sign"])
    outro = build_cin_qr({**cin_claims, "cpf": "99999999999"}, sign=cin_material["sign"])
    forjado = outro.rsplit(".", 1)[0] + "." + token.rsplit(".", 1)[1]

    result = checker.parse_qr_text(forjado)
    assert result.fields["cpf"] == "99999999999"
    assert not result.is_authentic


def test_emissor_diferente_de_mjsp(checker, cin_material, cin_claims):
    token = build_cin_qr({**cin_claims, "iss": "OUTRO"}, sign=cin_material["sign"])
    result = checker.parse_qr_text(token)

    assert result.is_authentic  # a assinatura confere...
    assert not result.is_valid  # ...mas o app rejeitaria o emissor
    assert any("emissor inesperado" in e for e in result.errors)


def test_sem_cpf(checker, cin_material, cin_claims):
    claims = {k: v for k, v in cin_claims.items() if k != "cpf"}
    result = checker.parse_qr_text(build_cin_qr(claims, sign=cin_material["sign"]))

    assert result.is_parsed
    assert not result.is_valid
    assert any("'cpf'" in e for e in result.errors)


def test_url_sem_uuid(checker, cin_material, cin_claims):
    token = build_cin_qr(
        {**cin_claims, "url": "https://cin.mj.gov.br/validar/"}, sign=cin_material["sign"]
    )
    result = checker.parse_qr_text(token)

    assert result.data.uuid is None
    assert not result.is_valid
    assert any("UUID" in e for e in result.errors)


def test_url_ausente(checker, cin_material, cin_claims):
    claims = {k: v for k, v in cin_claims.items() if k != "url"}
    result = checker.parse_qr_text(build_cin_qr(claims, sign=cin_material["sign"]))

    assert any("'url'" in e for e in result.errors)


def test_iat_vira_data_de_emissao(checker, cin_material, cin_claims):
    token = build_cin_qr({**cin_claims, "iat": 1750000000}, sign=cin_material["sign"])
    result = checker.parse_qr_text(token)

    assert result.issued_at == datetime.fromtimestamp(1750000000, tz=timezone.utc)


def test_exp_no_passado_marca_vencido(checker, cin_material, cin_claims):
    claims = {k: v for k, v in cin_claims.items() if k != "dvd"}
    token = build_cin_qr({**claims, "exp": 1000000000}, sign=cin_material["sign"])
    result = checker.parse_qr_text(token, now=datetime(2026, 1, 1, tzinfo=timezone.utc))

    assert result.is_expired is True
    assert not result.is_valid


def test_sem_dvd_nem_exp_nao_define_expiracao(checker, cin_material, cin_claims):
    claims = {k: v for k, v in cin_claims.items() if k != "dvd"}
    result = checker.parse_qr_text(build_cin_qr(claims, sign=cin_material["sign"]))
    assert result.is_expired is None
    assert result.expires_on is None


def test_algoritmo_nao_suportado(checker, cin_material, cin_claims):
    token = build_cin_qr(
        cin_claims, sign=cin_material["sign"], header={"alg": "HS256", "typ": "JWT"}
    )
    result = checker.parse_qr_text(token)

    assert result.is_parsed
    assert not result.is_authentic
    assert any("HS256" in e for e in result.errors)


def test_verificacao_desabilitada(cin_key_store, cin_material, cin_claims):
    checker = DigitalDocumentChecker(cin_keys=cin_key_store, verify_signature=False)
    result = checker.parse_qr_text(build_cin_qr(cin_claims, sign=cin_material["sign"]))

    assert result.is_parsed
    assert not result.signature.checked
    assert not result.is_authentic


def test_chave_de_producao_rejeita_token_de_teste(cin_material, cin_claims):
    """Sem passar um store, valem as chaves reais do app — o token de teste falha."""
    result = DigitalDocumentChecker().parse_qr_text(
        build_cin_qr(cin_claims, sign=cin_material["sign"])
    )
    assert result.is_parsed
    assert not result.is_authentic
    assert result.signature.candidates_tried == 1


def test_ambiente_curinga_tenta_todas_as_chaves(cin_material, cin_claims):
    checker = DigitalDocumentChecker(cin_environment="*")
    result = checker.parse_qr_text(build_cin_qr(cin_claims, sign=cin_material["sign"]))
    assert result.signature.candidates_tried == len(default_cin_keys())


# --------------------------------------------------------------------------- #
# Chaves embarcadas / JWS
# --------------------------------------------------------------------------- #
def test_chaves_embarcadas_do_app():
    store = default_cin_keys()
    prod = store.get()

    assert store.default_id == "PROD"
    assert prod.id == "PROD"
    assert prod.curve == "P-521"
    assert prod.base_url == "https://cin.mj.gov.br/api/"
    assert {key.id for key in store} == {"PROD", "HML", "TST"}


def test_chaves_embarcadas_carregam_no_cryptography():
    from digital_document_checker import crypto

    for key in default_cin_keys():
        assert crypto.load_ec_jwk(key.jwk).curve.name == "secp521r1"


def test_deteccao_de_jws_compacto(cin_material, cin_claims):
    assert looks_like_compact_jws(build_cin_qr(cin_claims, sign=cin_material["sign"]))
    assert not looks_like_compact_jws(b"\x00\x01\x02")
    assert not looks_like_compact_jws("a.b")
    assert not looks_like_compact_jws("a.b.c.d")


def test_parse_compact_jws_rejeita_payload_nao_objeto():
    from .conftest import b64url

    token = f"{b64url(b'{}')}.{b64url(b'[1,2]')}.{b64url(b'sig')}"
    with pytest.raises(ParseError, match="não é um objeto"):
        parse_compact_jws(token)


def test_handler_nao_participa_do_registro_por_template():
    from digital_document_checker.documents import find_handler

    assert not CINHandler().matches(4, None)
    assert find_handler(4, None).type_name != "cin"


def test_qrcode_vio_continua_no_caminho_do_envelope(rsa_material, cert_store, template_store):
    """Um QRCode binário do padrão VIO não pode cair na rota da CIN."""
    from .conftest import build_v2_qr

    qr = build_v2_qr(
        "NOME^123^" + "^" * 16, template_id=4, timestamp=0x60000000, sign=rsa_material["sign"]
    )
    result = DigitalDocumentChecker(cert_store, template_store).parse_bytes(qr)

    assert result.document_type == "cnh"
    assert result.header_format == "hex"
