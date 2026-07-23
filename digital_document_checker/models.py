"""Modelos de dados da biblioteca."""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


# --------------------------------------------------------------------------- #
# Metadados (certificados / templates)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Certificate:
    """Certificado (chave pública) usado para assinar um grupo de templates."""

    id: str
    group_id: Optional[str]
    public_key_b64: str
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None

    @property
    def public_key_der(self) -> bytes:
        return base64.b64decode(self.public_key_b64)

    def is_valid_at(self, moment: datetime) -> bool:
        if self.valid_from is not None and moment < self.valid_from:
            return False
        if self.valid_until is not None and moment > self.valid_until:
            return False
        return True

    def is_revoked_at(self, moment: datetime) -> bool:
        return self.revoked_at is not None and moment >= self.revoked_at


@dataclass(frozen=True)
class TemplateField:
    name: str
    label: Optional[str] = None


@dataclass(frozen=True)
class Template:
    """Descrição de um tipo de documento emitido (``templates.json``)."""

    id: int
    name: Optional[str] = None
    owner: Optional[str] = None
    owner_id: Optional[int] = None
    fields: tuple[TemplateField, ...] = ()
    certificate_group: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    sandbox: bool = False

    @property
    def field_names(self) -> list[str]:
        return [f.name for f in self.fields]


# --------------------------------------------------------------------------- #
# Envelope / payload
# --------------------------------------------------------------------------- #
@dataclass
class Envelope:
    """Cabeçalho do QRCode: data de emissão + versão do envelope."""

    raw: bytes
    header_format: str  # "hex" (10 bytes ASCII) ou "binary" (5 bytes)
    version: int
    issued_at: datetime
    issued_timestamp: int
    payload: bytes

    @property
    def signed_header(self) -> bytes:
        """Cabeçalho usado no dado assinado.

        O app **sempre** reconstrói o cabeçalho como 8 dígitos hexadecimais de
        timestamp + 2 de versão, em minúsculas e ISO-8859-1 — inclusive quando
        o QRCode trouxe o cabeçalho binário de 5 bytes. Por isso o dado
        assinado não usa :attr:`raw` diretamente.
        """
        return f"{self.issued_timestamp:08x}{self.version:02x}".encode("latin-1")


@dataclass
class RawPayload:
    """Resultado bruto do parsing específico de cada versão de envelope."""

    template_id: int
    signed_data: bytes
    signature: bytes
    fields_raw: Optional[str] = None
    field_values: list[str] = field(default_factory=list)
    photo: Optional[bytes] = None  # imagem com o magic (ex.: ``BPG``)
    extra: Optional[bytes] = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class SignatureInfo:
    """Detalhes da verificação da assinatura digital."""

    checked: bool = False
    is_authentic: bool = False
    algorithm: Optional[str] = None
    certificate_id: Optional[str] = None
    certificate_group: Optional[str] = None
    candidates_tried: int = 0
    reason: Optional[str] = None
    signature: Optional[bytes] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "checked": self.checked,
            "is_authentic": self.is_authentic,
            "algorithm": self.algorithm,
            "certificate_id": self.certificate_id,
            "certificate_group": self.certificate_group,
            "candidates_tried": self.candidates_tried,
            "reason": self.reason,
        }


@dataclass
class Photo:
    """Foto embarcada no QRCode."""

    data: bytes
    format: Optional[str] = None  # BPG, PNG, JPEG, ...

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self.data)

    def to_png(self, *, decoder: Optional[str] = None) -> bytes:
        """Converte a imagem para PNG (requer ``bpgdec`` no PATH para BPG)."""
        from .images import to_png

        return to_png(self, decoder=decoder)

    def save(self, path: str, *, as_png: bool = False, decoder: Optional[str] = None) -> str:
        from .images import save

        return save(self, path, as_png=as_png, decoder=decoder)


@dataclass
class DocumentResult:
    """Resultado completo da leitura de um documento digital.

    O parsing é sempre executado — mesmo quando a assinatura não confere ou o
    documento está vencido. Os campos ``is_*`` descrevem o estado encontrado e
    ``errors``/``warnings`` explicam o porquê.
    """

    # --- identificação -------------------------------------------------- #
    document_type: str = "unknown"
    document_name: Optional[str] = None
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    template_owner: Optional[str] = None
    template: Optional[Template] = None

    # --- envelope ------------------------------------------------------- #
    qr_version: Optional[int] = None
    header_format: Optional[str] = None
    issued_at: Optional[datetime] = None

    # --- conteúdo ------------------------------------------------------- #
    fields: dict[str, Any] = field(default_factory=dict)
    raw_fields: list[str] = field(default_factory=list)
    fields_raw_string: Optional[str] = None
    data: Optional[Any] = None  # objeto tipado do submódulo do documento
    photo: Optional[Photo] = None
    extra: Optional[bytes] = None

    # --- estado --------------------------------------------------------- #
    is_parsed: bool = False
    is_authentic: bool = False
    is_signature_checked: bool = False
    is_expired: Optional[bool] = None
    is_valid: bool = False
    is_sandbox: bool = False
    is_known_template: bool = False
    expires_on: Optional[datetime] = None
    signature: SignatureInfo = field(default_factory=SignatureInfo)

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # --- bruto ---------------------------------------------------------- #
    raw: Optional[bytes] = None
    signed_data: Optional[bytes] = None

    def add_error(self, message: str) -> None:
        if message not in self.errors:
            self.errors.append(message)

    def add_warning(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def get(self, name: str, default: Any = None) -> Any:
        return self.fields.get(name, default)

    def to_dict(self, *, include_raw: bool = False) -> dict[str, Any]:
        def _dt(value: Optional[datetime]) -> Optional[str]:
            return value.isoformat() if value else None

        out: dict[str, Any] = {
            "document_type": self.document_type,
            "document_name": self.document_name,
            "template": {
                "id": self.template_id,
                "name": self.template_name,
                "owner": self.template_owner,
                "known": self.is_known_template,
                "sandbox": self.is_sandbox,
            },
            "qr": {
                "version": self.qr_version,
                "header_format": self.header_format,
                "issued_at": _dt(self.issued_at),
            },
            "fields": self.fields,
            "raw_fields": self.raw_fields,
            "status": {
                "is_parsed": self.is_parsed,
                "is_authentic": self.is_authentic,
                "is_signature_checked": self.is_signature_checked,
                "is_expired": self.is_expired,
                "is_valid": self.is_valid,
                "expires_on": _dt(self.expires_on),
            },
            "signature": self.signature.to_dict(),
            "photo": {
                "present": self.photo is not None,
                "format": self.photo.format if self.photo else None,
                "size": len(self.photo.data) if self.photo else 0,
            },
            "errors": self.errors,
            "warnings": self.warnings,
        }
        if include_raw:
            out["raw"] = base64.b64encode(self.raw).decode() if self.raw else None
            out["signed_data"] = (
                base64.b64encode(self.signed_data).decode() if self.signed_data else None
            )
            out["photo_data"] = (
                base64.b64encode(self.photo.data).decode() if self.photo else None
            )
        return out

    def __str__(self) -> str:  # pragma: no cover - representação amigável
        status = "AUTÊNTICO" if self.is_authentic else "NÃO AUTENTICADO"
        if self.is_expired:
            status += " / VENCIDO"
        return f"<{self.document_type} template={self.template_id} {status}>"
