"""Digital Document Checker.

Biblioteca modular para *parsing*, verificação e validação de documentos
digitais brasileiros codificados em QRCode: o padrão SERPRO/VIO (CNH, DNI,
RG Digital) e a CIN — Carteira de Identidade Nacional, cujo QRCode é um JWT
assinado (ES512) pelo MJSP.

Uso rápido::

    from digital_document_checker import DigitalDocumentChecker

    checker = DigitalDocumentChecker()
    result = checker.parse_pdf("cnh.pdf")
    print(result.document_type, result.is_authentic, result.is_expired)
    print(result.fields)
"""

from __future__ import annotations

from .checker import DigitalDocumentChecker
from .exceptions import (
    DecodeError,
    DigitalDocumentError,
    MissingDependencyError,
    ParseError,
    QRCodeNotFoundError,
    UnsupportedVersionError,
)
from .models import (
    Certificate,
    CINKey,
    DocumentResult,
    Envelope,
    Photo,
    SignatureInfo,
    Template,
)
from .registry import CertificateStore, CINKeyStore, TemplateStore
from .__meta__ import __version__

__all__ = [
    "DigitalDocumentChecker",
    "DocumentResult",
    "SignatureInfo",
    "Photo",
    "Certificate",
    "CINKey",
    "Template",
    "Envelope",
    "CertificateStore",
    "CINKeyStore",
    "TemplateStore",
    "DigitalDocumentError",
    "ParseError",
    "DecodeError",
    "UnsupportedVersionError",
    "QRCodeNotFoundError",
    "MissingDependencyError",
    "__version__",
]
