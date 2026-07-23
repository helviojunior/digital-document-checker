"""Exemplo: ler e validar uma CNH digital a partir de um PDF ou imagem."""

from __future__ import annotations

import sys

from digital_document_checker import DigitalDocumentChecker


def main(path: str) -> None:
    checker = DigitalDocumentChecker()
    result = checker.parse_file(path)

    print(f"Tipo:       {result.document_name} ({result.document_type})")
    print(f"Parseado:   {result.is_parsed}")
    print(f"Autêntico:  {result.is_authentic} ({result.signature.algorithm})")
    print(f"Vencido:    {result.is_expired}")
    print(f"Válido:     {result.is_valid}")
    print("Campos:")
    for name, value in result.fields.items():
        if not name.startswith("_"):
            print(f"  - {name}: {value}")

    if result.photo:
        out = "foto.png"
        try:
            result.photo.save(out, as_png=True)
            print(f"Foto salva em {out}")
        except Exception as exc:  # noqa: BLE001
            print(f"Foto embarcada ({result.photo.format}); conversão falhou: {exc}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("uso: python examples/parse_cnh.py <arquivo.pdf|.png|.jpg>")
        raise SystemExit(1)
    main(sys.argv[1])
