"""Testes da leitura do QRCode em imagens.

Cobrem as duas armadilhas encontradas em documentos reais: a presença de
códigos de barras 1D ao lado do QRCode e QRCodes pequenos em digitalizações.
"""

import pytest

from digital_document_checker.exceptions import QRCodeNotFoundError
from digital_document_checker.qr import decode_qr, read_qr_from_image

pytest.importorskip("PIL")
pytest.importorskip("pyzbar.pyzbar")
qrcode = pytest.importorskip("qrcode")

from PIL import Image  # noqa: E402


PAYLOAD = "eyJhbGciOiJFUzUxMiJ9.eyJpc3MiOiJNSlNQIn0.QUJD"


def make_qr(data: str, *, box_size: int = 6) -> Image.Image:
    img = qrcode.make(data, box_size=box_size, border=4)
    return img.get_image().convert("RGB")


def paste_on_page(symbol: Image.Image, *, page=(1200, 1700), at=(700, 200)) -> Image.Image:
    page_img = Image.new("RGB", page, "white")
    page_img.paste(symbol, at)
    return page_img


def test_le_qrcode_simples():
    assert read_qr_from_image(make_qr(PAYLOAD)) == PAYLOAD.encode()


def test_qrcode_pequeno_exige_ampliacao():
    """QRCode com módulos de 1px falha no zbar sem o escalonamento."""
    small = make_qr(PAYLOAD, box_size=1)
    page = paste_on_page(small)

    assert decode_qr(page, upscale_steps=(1,)) is None  # sem ampliação, não acha
    assert decode_qr(page) == PAYLOAD.encode()  # com a escada padrão, acha


def test_codigo_de_barras_1d_nao_e_confundido_com_qrcode():
    """Um CODE128 sozinho não pode ser devolvido como conteúdo de QRCode."""
    barcode = pytest.importorskip("barcode")
    from barcode.writer import ImageWriter

    code = barcode.get("code128", "142602453", writer=ImageWriter())
    image = code.render(writer_options={"module_height": 15.0, "quiet_zone": 6.5})

    assert decode_qr(image) is None
    with pytest.raises(QRCodeNotFoundError) as exc:
        read_qr_from_image(image)
    assert "código(s) de barras" in str(exc.value)


def test_pagina_em_branco():
    with pytest.raises(QRCodeNotFoundError, match="nenhum QRCode encontrado"):
        read_qr_from_image(Image.new("RGB", (600, 600), "white"))


def test_aceita_caminho_e_bytes(tmp_path):
    import io

    path = tmp_path / "qr.png"
    make_qr(PAYLOAD).save(path)

    assert read_qr_from_image(str(path)) == PAYLOAD.encode()

    buffer = io.BytesIO()
    make_qr(PAYLOAD).save(buffer, format="PNG")
    assert read_qr_from_image(buffer.getvalue()) == PAYLOAD.encode()


def test_pdf_com_qrcode_pequeno(tmp_path):
    fitz = pytest.importorskip("fitz")

    png = tmp_path / "page.png"
    paste_on_page(make_qr(PAYLOAD, box_size=1)).save(png)

    pdf_path = tmp_path / "doc.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(fitz.Rect(0, 0, 595, 842), filename=str(png))
    doc.save(pdf_path)
    doc.close()

    from digital_document_checker.qr import read_qr_from_pdf

    assert read_qr_from_pdf(str(pdf_path)) == PAYLOAD.encode()
