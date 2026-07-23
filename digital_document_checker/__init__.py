"""Digital Document Checker.

Biblioteca modular para *parsing*, verificação e validação de documentos
digitais brasileiros codificados em QRCode (padrão SERPRO/VIO), com a CNH como
primeiro tipo suportado.

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
    DocumentResult,
    Envelope,
    Photo,
    SignatureInfo,
    Template,
)
from .registry import CertificateStore, TemplateStore
from .__meta__ import __version__

__all__ = [
    "DigitalDocumentChecker",
    "DocumentResult",
    "SignatureInfo",
    "Photo",
    "Certificate",
    "Template",
    "Envelope",
    "CertificateStore",
    "TemplateStore",
    "DigitalDocumentError",
    "ParseError",
    "DecodeError",
    "UnsupportedVersionError",
    "QRCodeNotFoundError",
    "MissingDependencyError",
    "__version__",
]
