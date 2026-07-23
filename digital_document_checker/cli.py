"""Interface de linha de comando.

Uso::

    python -m digital_document_checker <arquivo.pdf|.png|.jpg> [--json] [--save-photo foto.png]
"""

from __future__ import annotations

import argparse
import json
import sys

from . import DigitalDocumentChecker
from .exceptions import DigitalDocumentError


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="digital_document_checker",
        description="Parsing e validação de documentos digitais (CNH e outros).",
    )
    parser.add_argument("arquivo", help="PDF ou imagem contendo o QRCode")
    parser.add_argument("--json", action="store_true", help="saída em JSON")
    parser.add_argument(
        "--include-raw", action="store_true", help="inclui bytes brutos no JSON"
    )
    parser.add_argument(
        "--no-verify", action="store_true", help="não verifica a assinatura"
    )
    parser.add_argument("--save-photo", metavar="CAMINHO", help="salva a foto embarcada")
    parser.add_argument(
        "--dpi", type=int, default=300, help="DPI ao rasterizar PDFs (padrão: 300)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    checker = DigitalDocumentChecker(verify_signature=not args.no_verify)

    try:
        result = checker.parse_file(args.arquivo, now=None)
    except DigitalDocumentError as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 2

    if args.save_photo and result.photo:
        try:
            saved = result.photo.save(
                args.save_photo, as_png=args.save_photo.lower().endswith(".png")
            )
            print(f"foto salva em {saved}", file=sys.stderr)
        except DigitalDocumentError as exc:
            print(f"não foi possível salvar a foto: {exc}", file=sys.stderr)

    if args.json:
        print(json.dumps(result.to_dict(include_raw=args.include_raw), indent=2, ensure_ascii=False, default=str))
        return 0 if result.is_parsed else 1

    _print_human(result)
    return 0 if result.is_parsed else 1


def _print_human(result) -> None:
    def flag(value):
        if value is True:
            return "sim"
        if value is False:
            return "não"
        return "—"

    print(f"Tipo .............. {result.document_name} ({result.document_type})")
    print(f"Template .......... {result.template_id} — {result.template_owner or '?'}")
    print(f"Versão QR ......... {result.qr_version} ({result.header_format})")
    print(f"Emitido em ........ {result.issued_at}")
    print(f"Parseado .......... {flag(result.is_parsed)}")
    print(f"Autêntico ......... {flag(result.is_authentic)}  ({result.signature.algorithm or result.signature.reason or '—'})")
    print(f"Vencido ........... {flag(result.is_expired)}")
    print(f"Válido ............ {flag(result.is_valid)}")
    if result.fields:
        print("Campos:")
        for key, value in result.fields.items():
            if key.startswith("_"):
                continue
            print(f"  {key:<28} {value}")
    if result.photo:
        print(f"Foto .............. {result.photo.format}, {len(result.photo.data)} bytes")
    for warning in result.warnings:
        print(f"  aviso: {warning}")
    for error in result.errors:
        print(f"  erro:  {error}")


if __name__ == "__main__":
    raise SystemExit(main())
