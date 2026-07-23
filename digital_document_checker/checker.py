"""Orquestrador principal: parsing + verificação + validação.

Princípios (conforme requisitos do projeto):

* O **parsing ocorre sempre**, independente de validade ou autenticidade.
* O retorno traz **todos os dados disponíveis** mais os campos de estado
  (``is_parsed``, ``is_authentic``, ``is_valid``, ``is_expired`` ...).
* Erros de assinatura/expiração **não** interrompem o parsing — são reportados
  em ``errors`` / ``warnings``.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Optional

from . import crypto
from .documents import find_handler
from .exceptions import ParseError
from .formats import get_format, parse_envelope
from .images import make_photo
from .models import DocumentResult, SignatureInfo
from .registry import (
    CertificateStore,
    TemplateStore,
    default_certificates,
    default_templates,
)


class DigitalDocumentChecker:
    """Ponto de entrada da biblioteca."""

    def __init__(
        self,
        certificates: Optional[CertificateStore] = None,
        templates: Optional[TemplateStore] = None,
        *,
        verify_signature: bool = True,
    ) -> None:
        self.certificates = certificates or default_certificates()
        self.templates = templates or default_templates()
        self.verify_signature = verify_signature

    # ------------------------------------------------------------------ #
    # Entradas
    # ------------------------------------------------------------------ #
    def parse_bytes(
        self, data: bytes, *, now: Optional[datetime] = None
    ) -> DocumentResult:
        """Interpreta os bytes brutos de um QRCode."""
        return self._process(data, now=now)

    def parse_base64(self, b64: str, *, now: Optional[datetime] = None) -> DocumentResult:
        return self._process(base64.b64decode(b64), now=now)

    def parse_qr_text(self, text: str, *, now: Optional[datetime] = None) -> DocumentResult:
        """Interpreta o texto lido de um QRCode (Latin-1/UTF-8)."""
        try:
            data = text.encode("utf-8").decode("utf-8").encode("latin-1")
        except (UnicodeDecodeError, UnicodeEncodeError):
            data = text.encode("latin-1", errors="strict")
        return self._process(data, now=now)

    def parse_image(self, source, *, now: Optional[datetime] = None) -> DocumentResult:
        from .qr import read_qr_from_image

        return self._process(read_qr_from_image(source), now=now)

    def parse_pdf(self, path: str, *, dpi: int = 300, now: Optional[datetime] = None) -> DocumentResult:
        from .qr import read_qr_from_pdf

        return self._process(read_qr_from_pdf(path, dpi=dpi), now=now)

    def parse_file(self, path: str, *, now: Optional[datetime] = None) -> DocumentResult:
        """Detecta PDF vs imagem pelo conteúdo e faz o parsing."""
        with open(path, "rb") as handle:
            head = handle.read(5)
        if head.startswith(b"%PDF"):
            return self.parse_pdf(path, now=now)
        return self.parse_image(path, now=now)

    # ------------------------------------------------------------------ #
    # Núcleo
    # ------------------------------------------------------------------ #
    def _process(self, data: bytes, *, now: Optional[datetime]) -> DocumentResult:
        now = now or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        result = DocumentResult(raw=bytes(data))

        # 1) Envelope
        try:
            envelope = parse_envelope(data)
        except ParseError as exc:
            result.add_error(f"envelope inválido: {exc}")
            return result

        result.qr_version = envelope.version
        result.header_format = envelope.header_format
        result.issued_at = envelope.issued_at

        # 2) Formato específico da versão
        fmt = get_format(envelope.version)
        if fmt is None:
            result.add_error(f"versão de envelope não suportada: {envelope.version}")
            return result

        try:
            payload = fmt.parse(envelope)
        except ParseError as exc:
            result.add_error(f"falha no parsing do payload (v{envelope.version}): {exc}")
            return result
        except Exception as exc:  # noqa: BLE001
            result.add_error(f"erro inesperado no parsing (v{envelope.version}): {exc}")
            return result

        for warning in payload.warnings:
            result.add_warning(warning)

        result.is_parsed = True
        result.template_id = payload.template_id
        result.fields_raw_string = payload.fields_raw
        result.raw_fields = list(payload.field_values)
        result.signed_data = payload.signed_data
        result.photo = make_photo(payload.photo)
        if payload.extra:
            result.extra = payload.extra

        # 3) Template / tipo de documento
        template = self.templates.get(payload.template_id)
        result.template = template
        result.is_known_template = template is not None
        if template is not None:
            result.template_name = template.name
            result.template_owner = template.owner
            result.document_name = template.name
            result.is_sandbox = template.sandbox
            if template.valid_until is not None:
                result.expires_on = template.valid_until

        handler = find_handler(payload.template_id, template)
        result.document_type = handler.type_name
        if result.document_name is None:
            result.document_name = handler.display_name

        try:
            data_obj = handler.build(payload, template)
            result.data = data_obj
            result.fields = dict(data_obj.fields)
        except Exception as exc:  # noqa: BLE001
            result.add_warning(f"falha ao estruturar campos: {exc}")
            result.fields = {}

        # 4) Assinatura digital
        self._verify(result, payload, template, envelope, now)

        # 5) Expiração (data de validade do próprio documento, quando presente)
        self._check_expiration(result, now)

        # 6) Estado final
        result.is_valid = bool(
            result.is_parsed
            and result.is_authentic
            and not (result.is_expired is True)
        )
        return result

    # ------------------------------------------------------------------ #
    def _verify(self, result, payload, template, envelope, now) -> None:
        info = SignatureInfo(signature=payload.signature)
        result.signature = info

        if not self.verify_signature:
            info.reason = "verificação de assinatura desabilitada"
            return
        if not payload.signature:
            info.reason = "documento sem bloco de assinatura"
            result.add_warning(info.reason)
            return
        if not crypto.is_available():
            info.reason = "dependência 'cryptography' ausente"
            result.add_warning(info.reason)
            return

        group_id = template.certificate_group if template else None
        info.certificate_group = group_id
        issued_at = envelope.issued_at
        candidates = self.certificates.candidates(group_id, issued_at)

        info.checked = True
        info.candidates_tried = len(candidates)

        if not candidates:
            info.reason = "nenhum certificado válido para a data de emissão"
            result.add_error(info.reason)
            return

        for cert in candidates:
            ok, detail = crypto.verify(
                payload.signed_data, payload.signature, cert.public_key_b64
            )
            if ok:
                info.is_authentic = True
                info.algorithm = detail
                info.certificate_id = cert.id
                if cert.is_revoked_at(issued_at):
                    result.add_warning(
                        f"certificado {cert.id} estava revogado na emissão"
                    )
                break
        else:
            info.reason = "assinatura não confere com nenhum certificado do grupo"
            result.add_error(info.reason)

        result.is_authentic = info.is_authentic
        result.is_signature_checked = info.checked

    # ------------------------------------------------------------------ #
    def _check_expiration(self, result, now) -> None:
        """Deriva expiração a partir do campo de validade do documento."""
        validade = None
        if isinstance(result.fields, dict):
            validade = (
                result.fields.get("data_validade")
                or result.fields.get("validade")
            )
        parsed = _parse_br_date(validade) if validade else None
        if parsed is not None:
            result.expires_on = parsed
            result.is_expired = now.date() > parsed.date()
        elif result.expires_on is not None:
            result.is_expired = now > result.expires_on


def _parse_br_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
