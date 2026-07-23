# Digital Document Checker

[![Build](https://github.com/helviojunior/digital-document-checker/actions/workflows/build_and_publish.yml/badge.svg)](https://github.com/helviojunior/digital-document-checker/actions/workflows/build_and_publish.yml)
[![Build](https://github.com/helviojunior/digital-document-checker/actions/workflows/build_and_test.yml/badge.svg)](https://github.com/helviojunior/digital-document-checker/actions/workflows/build_and_test.yml)
[![Downloads](https://pepy.tech/badge/digital-document-checker/month)](https://pepy.tech/project/digital-document-checker)
[![Supported Versions](https://img.shields.io/pypi/pyversions/digital-document-checker.svg)](https://pypi.org/project/digital-document-checker)
[![Contributors](https://img.shields.io/github/contributors/helviojunior/digital-document-checker.svg)](https://github.com/helviojunior/digital-document-checker/graphs/contributors)
[![PyPI version](https://img.shields.io/pypi/v/digital-document-checker.svg)](https://pypi.org/project/digital-document-checker/)
[![License: MIT](https://img.shields.io/pypi/l/digital-document-checker.svg)](https://github.com/helviojunior/digital-document-checker/blob/main/LICENSE)

Biblioteca Python **modular** para *parsing*, verificação e validação de
documentos digitais brasileiros codificados em QRCode (padrão SERPRO / VIO /
Carteira Digital de Trânsito).

Tipos de documento já com submódulo próprio:

| Tipo         | Módulo                      | Templates    | Emissor   | Status        |
|--------------|-----------------------------|--------------|-----------|---------------|
| **CNH**      | `documents/cnh.py`          | 2, 4, 83     | SENATRAN  | verificado    |
| **DNI**      | `documents/dni.py`          | 8, 9, 73     | TSE       | experimental¹ |
| **RG Digital** | `documents/rg.py`         | 91, 92       | GovBr     | experimental¹ |

A arquitetura permite adicionar outros tipos (CRLV, identidades funcionais, ...)
como submódulos independentes — veja
[Adicionando um novo tipo de documento](#adicionando-um-novo-tipo-de-documento).

> ¹ *Experimental*: parsing implementado a partir da engenharia reversa do app
> oficial, ainda **não validado contra amostras reais** desses documentos.

> ⚠️ **Leia o [Disclaimer / Aviso Legal](#disclaimer--aviso-legal) antes de usar.**
> Projeto **pessoal**, sem qualquer garantia. O uso é **por sua conta e risco**.

## Objetivo

O objetivo deste projeto é oferecer uma forma **programática e aberta** de:

- **Extrair** (*parsing*) todos os dados contidos no QRCode de um documento
  digital brasileiro — nome, CPF, categoria, validade, foto, etc.
- **Verificar** a autenticidade da assinatura digital contra as chaves públicas
  oficiais (SENATRAN/SERPRO), quando disponíveis.
- **Validar** o estado do documento (autêntico, vencido, sandbox, template
  conhecido) devolvendo um resultado estruturado e fácil de consumir.

O *parsing* **sempre** acontece — mesmo que a assinatura não confira ou o
documento esteja vencido —, de modo que você sempre recebe os dados
disponíveis acompanhados dos indicadores de estado.

## Princípios de projeto

- **O parsing sempre ocorre**, independentemente de validade ou autenticidade.
  Um documento com assinatura inválida ou vencido ainda tem todos os seus
  campos extraídos.
- O resultado (`DocumentResult`) traz **todos os dados disponíveis** mais campos
  de estado padronizados: `is_parsed`, `is_authentic`, `is_signature_checked`,
  `is_expired`, `is_valid`, além de `errors` e `warnings`.
- **Modular por tipo**: cada documento tem seu submódulo em
  `digital_document_checker/documents/` com um `DocumentHandler`.

## Instalação

```bash
pip install -e .            # núcleo (parsing + verificação de assinatura)
pip install -e ".[full]"    # + leitura de QRCode em imagens e PDFs
```

Dependências opcionais:

| Recurso                         | Pacotes                     |
|---------------------------------|-----------------------------|
| Verificação de assinatura       | `cryptography` (núcleo)     |
| Ler QRCode de imagem            | `pyzbar`, `Pillow`          |
| Ler QRCode de PDF               | `PyMuPDF` (ou `pdf2image`)  |
| Converter a foto BPG para PNG   | binário `bpgdec` (libbpg)   |

> `pyzbar` requer a biblioteca nativa **zbar** (`brew install zbar` no macOS,
> `apt-get install libzbar0` no Linux).

## Uso rápido

```python
from digital_document_checker import DigitalDocumentChecker

checker = DigitalDocumentChecker()

result = checker.parse_pdf("cnh.pdf")          # ou parse_image / parse_bytes / parse_base64
print(result.document_type)                     # "cnh"
print(result.is_authentic, result.is_expired)   # True/False
print(result.fields["nome"], result.fields["cpf"])

if result.photo:
    result.photo.save("foto.png", as_png=True)  # BPG -> PNG (requer bpgdec)
```

Linha de comando:

```bash
python -m digital_document_checker cnh.pdf
python -m digital_document_checker cnh.pdf --json --save-photo foto.png
```

## Uso com Docker

A imagem já traz o projeto instalado (clonado no *build*) com todas as
dependências de leitura de QRCode e PDF (`pyzbar`/`zbar`, `Pillow`, `PyMuPDF`)
e o `bpgdec` (libbpg) **compilado**, habilitando a conversão da foto BPG → PNG
dentro do container.

Build:

```bash
docker build -t digital-document-checker .

# opcional: fixar um branch ou tag do repositório
docker build --build-arg GIT_REF=main -t digital-document-checker .
```

Execução — monte o diretório com seus arquivos em `/data`:

```bash
# saída legível
docker run --rm -v "$PWD:/data" digital-document-checker /data/cnh.pdf

# saída JSON
docker run --rm -v "$PWD:/data" digital-document-checker /data/cnh.pdf --json

# salvar a foto embarcada, convertida para PNG (bpgdec incluso na imagem)
docker run --rm -v "$PWD:/data" digital-document-checker \
    /data/cnh.pdf --save-photo /data/foto.png

# ajuda
docker run --rm digital-document-checker --help
```

> A conversão da foto **BPG → PNG** (`--save-photo *.png`) usa o `bpgdec`, que já
> vem compilado na imagem Docker. Fora do Docker, essa conversão específica exige
> o `bpgdec` (libbpg) no `PATH`; sem ele, a foto ainda é extraída em BPG e a
> extração dos dados e a verificação da assinatura **não** dependem disso.

## O que é verificado

1. **Envelope** — timestamp de emissão + versão (cabeçalho hexadecimal de 10
   bytes ou binário de 5 bytes).
2. **Formato** — o parser correto é escolhido pela versão (CNH = versão 2).
3. **Template** — `template_id` → tipo de documento, emissor e grupo de
   certificados (`data/templates.json`).
4. **Assinatura digital** — `SHA256withRSA` ou `SHA256withECDSA` contra as
   chaves públicas de `data/certificates.json`, considerando a janela de
   validade do certificado na data de emissão.
5. **Expiração** — a partir do campo de validade do próprio documento.

## Estrutura

```
digital_document_checker/
├── checker.py            # orquestrador (parse -> verifica -> valida)
├── models.py             # DocumentResult, Certificate, Template, Photo, ...
├── registry.py           # CertificateStore / TemplateStore (JSONs oficiais)
├── crypto.py             # verificação RSA / ECDSA
├── images.py, qr.py      # foto embarcada e leitura de QRCode
├── codecs/               # bits, alfabetos 6/7 bits, basE91
├── formats/              # parsers por versão de envelope (2 = CNH, 3 = DNI, ...)
│   ├── envelope.py
│   ├── v2_cnh.py         # CNH (verificado)
│   ├── v3_dni.py         # DNI (experimental)
│   ├── multiblock.py     # versões 4/5/6 (experimental)
│   └── v1_text.py        # versão 1 legada (experimental)
├── documents/            # submódulos por tipo de documento
│   ├── cnh.py            # CNH  <- verificado
│   ├── dni.py            # DNI  (experimental)
│   ├── rg.py             # RG Digital (experimental)
│   └── generic.py
└── data/                 # certificates.json, templates.json
```

## Adicionando um novo tipo de documento

```python
from digital_document_checker.documents import register_handler
from digital_document_checker.documents.base import DocumentHandler, DocumentData

class MeuDocHandler(DocumentHandler):
    type_name = "meu_doc"
    display_name = "Meu Documento"
    template_ids = (123,)

    def build(self, payload, template):
        # payload.field_values -> valores brutos
        return DocumentData(raw_fields=payload.field_values, fields={...})

register_handler(MeuDocHandler(), prepend=True)
```

## Notas sobre o formato (engenharia reversa)

- O conteúdo do QRCode é binário transportado como texto Latin-1.
- A CNH (versão 2) empacota os campos em **6 bits por caractere** (alfabeto
  ASCII 32–95), seguidos de **256 bytes de assinatura** e da **foto em BPG**.
- O decodificador de bits desta biblioteca foi validado byte-a-byte contra o
  decodificador do aplicativo oficial de referência.
- As versões 1, 4, 5 e 6 (outros tipos de documento) têm parsing estrutural
  implementado, porém ainda **não validados contra amostras reais** — marcados
  como experimentais no código.

## Disclaimer / Aviso Legal

> **Leia com atenção antes de utilizar.**

Este é um **projeto pessoal**, desenvolvido de forma independente e sem vínculo
com o SERPRO, o SENATRAN, o DENATRAN ou qualquer órgão governamental. Não se
trata de uma ferramenta oficial de validação.

O software é fornecido **"COMO ESTÁ" ("AS IS"), sem garantias de qualquer
natureza**, expressas ou implícitas, incluindo — mas não se limitando a —
garantias de comercialização, adequação a uma finalidade específica, exatidão,
integridade ou não violação.

- O projeto **pode conter falhas e bugs**. O resultado da verificação **pode
  gerar falsos-negativos e/ou falsos-positivos** (por exemplo, apontar como
  autêntico um documento fraudado, ou como inválido um documento legítimo).
- Os autores e colaboradores **NÃO se responsabilizam** por qualquer dano,
  prejuízo, perda financeira, fraude, decisão equivocada ou consequência de
  qualquer natureza decorrente, direta ou indiretamente, do uso — ou da
  impossibilidade de uso — desta biblioteca ou de seus resultados.
- **O uso é por sua conta e risco.** Não utilize este software como única fonte
  para decisões que envolvam dinheiro, segurança, identidade, obrigações legais
  ou qualquer situação crítica. Para validação com valor legal, utilize sempre
  os **canais e aplicativos oficiais**.
- Os metadados em `data/certificates.json` e `data/templates.json` são os dados
  públicos distribuídos com o aplicativo oficial de validação e podem estar
  **desatualizados**. Mantê-los atualizados é responsabilidade do usuário.

Ao utilizar este projeto, você **declara estar ciente e de acordo** com todos os
termos deste aviso. Ferramenta destinada a fins de **estudo, pesquisa e
verificação técnica**.

## Testes

```bash
pip install -e ".[dev]"
pytest
```
