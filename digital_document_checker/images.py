"""Utilidades de imagem: detecção de formato e conversão da foto embarcada.

A foto da CNH vem em BPG. A conversão para PNG requer ``bpgdec`` no PATH
(ou a libbpg dinâmica). PNG/JPEG são gravados diretamente.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Optional

from .exceptions import MissingDependencyError
from .models import Photo


def sniff_format(raw: bytes) -> Optional[str]:
    if not raw:
        return None
    if raw.startswith(b"BPG"):
        return "BPG"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if raw.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if raw.startswith(b"BM"):
        return "BMP"
    if raw[:4] in (b"II*\x00", b"MM\x00*"):
        return "TIFF"
    return None


def make_photo(raw: Optional[bytes]) -> Optional[Photo]:
    if not raw:
        return None
    return Photo(data=raw, format=sniff_format(raw))


def to_png(photo: Photo, *, decoder: Optional[str] = None) -> bytes:
    """Converte a foto para PNG. BPG exige ``bpgdec`` (ou informe ``decoder``)."""
    if photo.format == "PNG":
        return photo.data
    if photo.format == "BPG":
        return _bpg_to_png(photo.data, decoder=decoder)
    # tenta via Pillow para os demais formatos
    try:
        import io

        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise MissingDependencyError(
            "Pillow é necessário para converter esta imagem para PNG"
        ) from exc
    with Image.open(io.BytesIO(photo.data)) as img:
        buffer = io.BytesIO()
        img.convert("RGBA").save(buffer, format="PNG")
        return buffer.getvalue()


def _bpg_to_png(data: bytes, *, decoder: Optional[str] = None) -> bytes:
    binary = decoder or shutil.which("bpgdec")
    if not binary:
        raise MissingDependencyError(
            "bpgdec não encontrado no PATH — instale libbpg para converter a foto BPG"
        )
    with tempfile.TemporaryDirectory() as tmp:
        bpg_path = os.path.join(tmp, "in.bpg")
        png_path = os.path.join(tmp, "out.png")
        with open(bpg_path, "wb") as handle:
            handle.write(data)
        subprocess.run([binary, "-o", png_path, bpg_path], check=True)
        with open(png_path, "rb") as handle:
            return handle.read()


def save(photo: Photo, path: str, *, as_png: bool = False, decoder: Optional[str] = None) -> str:
    if as_png and photo.format != "PNG":
        data = to_png(photo, decoder=decoder)
    else:
        data = photo.data
    with open(path, "wb") as handle:
        handle.write(data)
    return path
