# Digital Document Checker

[![Build](https://github.com/helviojunior/digital-document-checker/actions/workflows/build_and_publish.yml/badge.svg)](https://github.com/helviojunior/digital-document-checker/actions/workflows/build_and_publish.yml)
[![Build](https://github.com/helviojunior/digital-document-checker/actions/workflows/build_and_test.yml/badge.svg)](https://github.com/helviojunior/digital-document-checker/actions/workflows/build_and_test.yml)
[![Downloads](https://pepy.tech/badge/digital-document-checker/month)](https://pepy.tech/project/digital-document-checker)
[![Supported Versions](https://img.shields.io/pypi/pyversions/digital-document-checker.svg)](https://pypi.org/project/digital-document-checker)
[![Contributors](https://img.shields.io/github/contributors/helviojunior/digital-document-checker.svg)](https://github.com/helviojunior/digital-document-checker/graphs/contributors)
[![PyPI version](https://img.shields.io/pypi/v/digital-document-checker.svg)](https://pypi.org/project/digital-document-checker/)
[![License: MIT](https://img.shields.io/pypi/l/digital-document-checker.svg)](https://github.com/helviojunior/digital-document-checker/blob/main/LICENSE)

Biblioteca Python **modular** para *parsing*, verificação e validação de
documentos digitais brasileiros codificados em QRCode — o padrão SERPRO / VIO /
Carteira Digital de Trânsito e a **CIN** (Carteira de Identidade Nacional).

Tipos de documento já com submódulo próprio:

| Tipo         | Módulo                      | Templates    | Emissor   | Status        |
|--------------|-----------------------------|--------------|-----------|---------------|
| **CNH**      | `documents/cnh.py`          | 2, 4, 83     | SENATRAN  | verificado    |
| **DNI**      | `documents/dni.py`          | 8, 9, 73     | TSE       | experimental¹ |
| **RG Digital** | `documents/rg.py`         | 91, 92       | GovBr     | experimental¹ |
| **CIN**      | `documents/cin.py`          | — (JWT)      | MJSP      | experimental¹ |

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
python -m digital_document_checker cin.jpg              # CIN: detectada automaticamente
```

### CIN — Carteira de Identidade Nacional

O QRCode impresso no **verso da CIN** não usa o envelope binário do padrão VIO:
seu conteúdo é um **JWT assinado** (`ES512`, curva P-521) emitido pelo MJSP. A
detecção é automática — o mesmo `DigitalDocumentChecker` reconhece o formato e
escolhe o caminho certo.

```python
result = checker.parse_image("cin_verso.jpg")   # ou parse_qr_text(<token JWT>)

result.document_type       # "cin"
result.header_format       # "jws"
result.is_authentic        # assinatura ES512 conferida contra a chave do app
result.signature.algorithm # "ES512"

result.data.cpf                # "12345678901"
result.data.cpf_formatado      # "123.456.789-01"
result.data.data_nascimento    # "07/08/1981"   (claim 'dns')
result.data.data_validade      # "02/02/2036"   (claim 'dvd')
result.data.url                # "https://cin.mj.gov.br/cidadao/<uuid>"
result.data.uuid               # chave usada pelo app na consulta online
result.data.outras_claims      # demais claims do JWT
```

O QRCode carrega **CPF, data de nascimento e data de validade**. Nome, filiação
e sexo só existem na leitura *online*, consultados na API do MJSP a partir do
`uuid` — esta biblioteca **não** faz chamadas de rede.

As checagens reproduzem `processQrCode` do app: `cpf` presente, `iss == "MJSP"`,
`url` presente e terminando em UUID, e assinatura válida. Cada checagem
reprovada vira um item em `result.errors` — os campos continuam sendo extraídos.

As chaves públicas ficam em `data/cin_keys.json` (ambientes `PROD`, `HML` e
`TST` do app; `PROD` é o padrão, como em `CURRENT_ENV`):

```bash
python -m digital_document_checker cin.jpg --cin-env '*'   # tenta todos os ambientes
```

```python
from digital_document_checker import CINKeyStore, DigitalDocumentChecker

checker = DigitalDocumentChecker(cin_keys=CINKeyStore.from_file("minhas_chaves.json"))
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

**Padrão VIO/SERPRO (CNH, DNI, RG Digital):**

1. **Envelope** — timestamp de emissão + versão (cabeçalho hexadecimal de 10
   bytes ou binário de 5 bytes).
2. **Formato** — o parser correto é escolhido pela versão (CNH = versão 2).
3. **Template** — `template_id` → tipo de documento, emissor e grupo de
   certificados (`data/templates.json`).
4. **Assinatura digital** — `SHA256withRSA` ou `SHA256withECDSA` contra as
   chaves públicas de `data/certificates.json`, considerando a janela de
   validade do certificado na data de emissão.
5. **Expiração** — a partir do campo de validade do próprio documento.

**CIN:**

1. **Formato** — JWS compacto de três segmentos (`header.payload.signature`).
2. **Claims** — `cpf` presente, `iss == "MJSP"`, `url` presente e terminando em
   um UUID.
3. **Assinatura digital** — `ES512` (P-521) sobre `header.payload`, contra a
   chave pública JWK de `data/cin_keys.json`.
4. **Expiração** — pela claim `dvd` (a validade impressa no cartão) ou, na
   falta dela, pelo `exp` do JWT.

## Estrutura

```
digital_document_checker/
├── checker.py            # orquestrador (parse -> verifica -> valida)
├── models.py             # DocumentResult, Certificate, Template, Photo, ...
├── registry.py           # CertificateStore / TemplateStore / CINKeyStore
├── crypto.py             # verificação RSA / ECDSA / JWS (ES256-512)
├── images.py, qr.py      # foto embarcada e leitura de QRCode
├── codecs/               # bits, alfabetos 6/7 bits, basE91
├── formats/              # parsers por versão de envelope (2 = CNH, 3 = DNI, ...)
│   ├── envelope.py
│   ├── jws.py            # JWS compacto (CIN)
│   ├── v2_cnh.py         # CNH (verificado)
│   ├── v3_dni.py         # DNI (experimental)
│   ├── multiblock.py     # versões 4/5/6 (experimental)
│   └── v1_text.py        # versão 1 legada (experimental)
├── documents/            # submódulos por tipo de documento
│   ├── cnh.py            # CNH  <- verificado
│   ├── dni.py            # DNI  (experimental)
│   ├── rg.py             # RG Digital (experimental)
│   ├── cin.py            # CIN  (experimental)
│   └── generic.py
└── data/                 # certificates.json, templates.json, cin_keys.json
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

- O conteúdo do QRCode é binário transportado como texto Latin-1 (ISO-8859-1).
- A CNH (versão 2) empacota os campos em **6 bits por caractere** (alfabeto
  ASCII 32–95), seguidos de **256 bytes de assinatura** e da **foto em BPG**.
- O decodificador de bits desta biblioteca foi validado byte-a-byte contra o
  decodificador do aplicativo oficial de referência.
- O **dado assinado** nunca usa os bytes originais do cabeçalho: o app sempre o
  reconstrói como 8 dígitos hexadecimais de timestamp + 2 de versão, em
  minúsculas — inclusive quando o QRCode traz o cabeçalho binário de 5 bytes.
- Campos por versão: **1** basE91, **2** e **5** 6 bits, **4** 7 bits,
  **3** e **6** basE91. As versões 4, 5 e 6 também transportam a foto no bloco
  intermediário.
- As versões 1, 4, 5 e 6 (outros tipos de documento) têm parsing estrutural
  implementado, porém ainda **não validados contra amostras reais** — marcados
  como experimentais no código.
- Os arquivos `data/certificates.json` e `data/templates.json` acompanham o app
  oficial (última sincronização: VIO 2.4.5). A origem remota é
  `https://vio.serpro.gov.br/api/v2/{certificates,templates}`.

### CIN

- Origem: app **`identidade-nacional` 1.19.0** (React Native / Expo SDK 50). A
  lógica fica no bundle Hermes `assets/index.android.bundle`, não no DEX.
- O QRCode é um **JWS compacto** (`header.payload.signature` em base64url) —
  nada de envelope binário, timestamp ou `template_id`.
- Fluxo de `processQrCode`: decodifica o JWT → exige `cpf`, `iss == "MJSP"` e
  `url` string → valida a assinatura → extrai o UUID do fim da `url` com
  `/\/([0-9a-fA-F]{8}-...-[0-9a-fA-F]{12})$/`.
- A verificação da assinatura é delegada ao módulo nativo
  `IoReactNativeJwtModule.verify` (`@pagopa/io-react-native-jwt`), que usa o
  `ECDSAVerifier` do Nimbus com BouncyCastle. Consequências práticas: a
  assinatura vem no **formato JOSE** (`R || S`, 132 bytes para P-521) e não em
  DER, e **nenhuma claim padrão é validada** — nem `exp`, nem `nbf`.
- As chaves de `data/cin_keys.json` são as de `ENVIRONMENTS[*].publicKeyJWT`;
  o app usa `CURRENT_ENV = PROD`. `HML` e `TST` compartilham o mesmo par.
  **Validado contra uma CIN real**: a assinatura confere com a chave `PROD`.
- Claims observadas em documento real: `iss`, `url`, `cpf`, `dns` (nascimento) e
  `dvd` (validade). Não há `iat`, `exp` nem `kid`.
- A claim **`dvd`** não é usada pelo app 1.19.0 — ele só renderiza CPF e `dns` na
  tela offline —, mas o rótulo `dateValid` ("DATA DE VALIDADE") já existe em
  `commonStrings.qrCodeScreen.validateOff`. Aqui ela é lida e usada na expiração.
- Os demais dados vêm de `POST /api/dados` com o `uuid` — fora do escopo desta
  biblioteca, que não faz rede.

### Leitura do QRCode em digitalizações

Duas armadilhas encontradas em documentos reais e tratadas em `qr.py`:

- A CIN traz **códigos de barras 1D** (CODE39) ao lado do QRCode. Aceitar
  qualquer simbologia faz o leitor devolver o conteúdo errado — por isso a
  decodificação é restrita a `ZBarSymbol.QRCODE`.
- Em PDFs digitalizados o QRCode ocupa poucos pixels e o zbar falha na
  resolução original. A leitura escalona a imagem (1×, 2×, 3×, 4×) alternando
  `LANCZOS` (suaviza o ruído do scanner) e `NEAREST` (preserva QRCodes nítidos
  de um pixel por módulo), mais uma variante com contraste automático. PDFs
  ainda são re-renderizados no dobro do DPI antes de desistir.

## Disclaimer / Aviso Legal

> **Leia com atenção antes de utilizar.**

Este é um **projeto pessoal**, desenvolvido de forma independente e sem vínculo
com o SERPRO, o SENATRAN, o DENATRAN, o MJSP ou qualquer órgão governamental.
Não se trata de uma ferramenta oficial de validação.

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
- Os metadados em `data/certificates.json`, `data/templates.json` e
  `data/cin_keys.json` são os dados públicos distribuídos com os aplicativos
  oficiais de validação e podem estar **desatualizados**. Mantê-los atualizados
  é responsabilidade do usuário.

Ao utilizar este projeto, você **declara estar ciente e de acordo** com todos os
termos deste aviso. Ferramenta destinada a fins de **estudo, pesquisa e
verificação técnica**.

## Testes

```bash
pip install -e ".[dev]"
pytest
```
