# Digital Document Checker
#
# Imagem com o projeto instalado a partir do repositório oficial.
#
# Build:
#   docker build -t digital-document-checker .
#   # ou fixando um branch/tag:
#   docker build --build-arg GIT_REF=main -t digital-document-checker .
#
# Uso:
#   docker run --rm -v "$PWD:/data" digital-document-checker /data/cnh.pdf
#   docker run --rm -v "$PWD:/data" digital-document-checker /data/cnh.pdf --json
#
FROM python:3.12-slim

ARG GIT_REPO=https://github.com/helviojunior/digital_document_checker.git
ARG GIT_REF=main

# Dependências nativas:
#  - git                : clone do projeto
#  - libzbar0           : leitura de QRCode (pyzbar)
#  - libgl1/libglib2.0-0: runtime de imagem (Pillow/opencv-like)
#  - bpgenc/bpgdec      : não há pacote apt; a foto BPG é extraída, e a
#                         conversão para PNG exige 'bpgdec' (opcional).
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        libzbar0 \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# Clona e instala o projeto (com as dependências opcionais de QR/PDF).
RUN git clone --depth 1 --branch "${GIT_REF}" "${GIT_REPO}" digital_document_checker \
    && pip install --no-cache-dir "./digital_document_checker[full]"

# Diretório de trabalho para os arquivos do usuário (montado via -v).
WORKDIR /data

# Executa a CLI; argumentos do 'docker run' são repassados a ela.
ENTRYPOINT ["digital-document-checker"]
CMD ["--help"]
