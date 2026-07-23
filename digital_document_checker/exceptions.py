"""Exceções da biblioteca."""


class DigitalDocumentError(Exception):
    """Erro base."""


class ParseError(DigitalDocumentError):
    """O conteúdo do QRCode não pôde ser interpretado."""


class UnsupportedVersionError(ParseError):
    """Versão de envelope não suportada."""


class DecodeError(ParseError):
    """Falha ao decodificar um bloco de dados (alfabeto / basE91 / bits)."""


class QRCodeNotFoundError(DigitalDocumentError):
    """Nenhum QRCode encontrado na imagem/PDF."""


class MissingDependencyError(DigitalDocumentError):
    """Dependência opcional ausente."""
