"""Leitura do QRCode a partir de imagens e PDFs.

O conteúdo do QRCode é binário transportado como texto Latin-1; a recuperação
dos bytes originais segue o mesmo caminho do app oficial::

    dados.decode("utf-8").encode("latin-1")
"""

from __future__ import annotations

from .exceptions import MissingDependencyError, QRCodeNotFoundError


def _decode_qr_bytes(raw_text_bytes: bytes) -> bytes:
    """Converte o texto do QRCode de volta para os bytes originais."""
    try:
        return raw_text_bytes.decode("utf-8").encode("latin-1")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return raw_text_bytes


def read_qr_from_image(source) -> bytes:
    """Lê o primeiro QRCode de uma imagem (caminho, bytes ou ``PIL.Image``)."""
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode as zbar_decode
    except ImportError as exc:  # pragma: no cover
        raise MissingDependencyError(
            "leitura de QRCode requer 'pyzbar' e 'Pillow'"
        ) from exc

    import io

    if isinstance(source, (str, bytes)) and not isinstance(source, (bytearray,)):
        if isinstance(source, bytes):
            image = Image.open(io.BytesIO(source))
        else:
            image = Image.open(source)
    else:
        image = source  # assume PIL.Image

    decoded = zbar_decode(image)
    if not decoded:
        raise QRCodeNotFoundError("nenhum QRCode encontrado na imagem")
    return _decode_qr_bytes(decoded[0].data)


def read_qr_from_pdf(path: str, *, dpi: int = 300) -> bytes:
    """Lê o primeiro QRCode de um PDF, renderizando as páginas como imagem."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        fitz = None

    if fitz is not None:
        from PIL import Image
        from pyzbar.pyzbar import decode as zbar_decode

        doc = fitz.open(path)
        try:
            zoom = dpi / 72
            matrix = fitz.Matrix(zoom, zoom)
            for page in doc:
                pixmap = page.get_pixmap(matrix=matrix)
                image = Image.frombytes(
                    "RGB", (pixmap.width, pixmap.height), pixmap.samples
                )
                decoded = zbar_decode(image)
                if decoded:
                    return _decode_qr_bytes(decoded[0].data)
        finally:
            doc.close()
        raise QRCodeNotFoundError("nenhum QRCode encontrado no PDF")

    # fallback: pdf2image
    try:
        from pdf2image import convert_from_path
        from pyzbar.pyzbar import decode as zbar_decode
    except ImportError as exc:  # pragma: no cover
        raise MissingDependencyError(
            "leitura de PDF requer 'PyMuPDF' ou 'pdf2image'"
        ) from exc

    for image in convert_from_path(path, dpi=dpi):
        decoded = zbar_decode(image)
        if decoded:
            return _decode_qr_bytes(decoded[0].data)
    raise QRCodeNotFoundError("nenhum QRCode encontrado no PDF")
