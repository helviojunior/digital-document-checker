# Digital Document Checker
#
# Imagem com o projeto instalado a partir do repositório oficial, incluindo o
# 'bpgdec' (libbpg) compilado para converter a foto BPG embarcada em PNG.
#
# Build:
#   docker build -t digital-document-checker .
#   # ou fixando um branch/tag:
#   docker build --build-arg GIT_REF=main -t digital-document-checker .
#
# Uso:
#   docker run --rm -v "$PWD:/data" digital-document-checker /data/cnh.pdf
#   docker run --rm -v "$PWD:/data" digital-document-checker /data/cnh.pdf --json
#   docker run --rm -v "$PWD:/data" digital-document-checker \
#       /data/cnh.pdf --save-photo /data/foto.png
#
# ---------------------------------------------------------------------------
# Estágio 1 — compila a libbpg (bpgdec / bpgenc)
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS bpg-builder

ARG LIBBPG_VERSION=0.9.8

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN curl -fsSL "https://bellard.org/bpg/libbpg-${LIBBPG_VERSION}.tar.gz" -o libbpg.tar.gz \
    && tar -xzf libbpg.tar.gz \
    && mv "libbpg-${LIBBPG_VERSION}" libbpg

WORKDIR /build/libbpg
# Para converter BPG -> PNG basta o decoder (bpgdec) — ele não depende de x265
# nem de cmake (isso é só do encoder). Desabilitamos o visualizador (SDL) e
# adicionamos flags de compatibilidade com o GCC atual (-fcommon evita erros
# de -fno-common) antes de compilar apenas o alvo 'bpgdec'.
RUN sed -i 's/^USE_BPGVIEW=y/USE_BPGVIEW=n/' Makefile \
    && sed -i 's#^CFLAGS+=-I\.#CFLAGS+=-I. -fcommon -Wno-implicit-function-declaration -Wno-format-truncation -Wno-stringop-overflow#' Makefile \
    && make -j"$(nproc)" bpgdec \
    && strip bpgdec

# ---------------------------------------------------------------------------
# Estágio 2 — imagem final
# ---------------------------------------------------------------------------
FROM python:3.12-slim

ARG GIT_REPO=https://github.com/helviojunior/digital_document_checker.git
ARG GIT_REF=main

# Dependências nativas:
#  - git                     : clone do projeto
#  - libzbar0                : leitura de QRCode (pyzbar)
#  - libgl1 / libglib2.0-0   : runtime de imagem (Pillow)
#  - libpng16-16             : runtime do binário bpgdec
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        libzbar0 \
        libgl1 \
        libglib2.0-0 \
        libpng16-16 \
    && rm -rf /var/lib/apt/lists/*

# Binário da libbpg (decoder) vindo do estágio de build.
COPY --from=bpg-builder /build/libbpg/bpgdec /usr/local/bin/bpgdec

WORKDIR /opt

# Clona e instala o projeto (com as dependências opcionais de QR/PDF).
RUN git clone --depth 1 --branch "${GIT_REF}" "${GIT_REPO}" digital_document_checker \
    && pip install --no-cache-dir "./digital_document_checker[full]"

# Diretório de trabalho para os arquivos do usuário (montado via -v).
WORKDIR /data

# Executa a CLI; argumentos do 'docker run' são repassados a ela.
ENTRYPOINT ["digital-document-checker"]
CMD ["--help"]
