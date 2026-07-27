"""Carregamento dos metadados: certificados, templates e chaves da CIN.

Os arquivos ``data/certificates.json`` e ``data/templates.json`` são os mesmos
distribuídos com o aplicativo oficial de validação. É possível substituí-los
por versões atualizadas via :meth:`CertificateStore.from_file` /
:meth:`TemplateStore.from_file`.

``data/cin_keys.json`` traz as chaves públicas JWK do app da Carteira de
Identidade Nacional (:class:`CINKeyStore`).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Optional

from .models import Certificate, CINKey, Template, TemplateField

DATA_DIR = Path(__file__).resolve().parent / "data"
CERTIFICATES_FILE = DATA_DIR / "certificates.json"
TEMPLATES_FILE = DATA_DIR / "templates.json"
CIN_KEYS_FILE = DATA_DIR / "cin_keys.json"


def parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Converte as datas ISO-8601 dos JSONs (com offset) em ``datetime`` aware."""
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class CertificateStore:
    """Coleção de certificados agrupados por ``certificate_group``."""

    def __init__(self, certificates: Iterable[Certificate]) -> None:
        self._certificates = list(certificates)
        self._by_group: dict[Optional[str], list[Certificate]] = {}
        for cert in self._certificates:
            self._by_group.setdefault(cert.group_id, []).append(cert)

    # -- construtores ---------------------------------------------------- #
    @classmethod
    def from_json(cls, payload: list[dict]) -> "CertificateStore":
        certs = []
        for item in payload:
            valid = item.get("valid") or {}
            certs.append(
                Certificate(
                    id=item.get("id"),
                    group_id=(item.get("group") or {}).get("id"),
                    public_key_b64=item.get("public_key", ""),
                    valid_from=parse_datetime(valid.get("from")),
                    valid_until=parse_datetime(valid.get("until")),
                    created_at=parse_datetime(item.get("created_at")),
                    updated_at=parse_datetime(item.get("updated_at")),
                    revoked_at=parse_datetime(item.get("revoked_at")),
                )
            )
        return cls(certs)

    @classmethod
    def from_file(cls, path: str | Path) -> "CertificateStore":
        with open(path, "r", encoding="utf-8") as handle:
            return cls.from_json(json.load(handle))

    @classmethod
    def default(cls) -> "CertificateStore":
        return cls.from_file(CERTIFICATES_FILE)

    # -- consultas ------------------------------------------------------- #
    def __iter__(self) -> Iterator[Certificate]:
        return iter(self._certificates)

    def __len__(self) -> int:
        return len(self._certificates)

    def by_group(self, group_id: Optional[str]) -> list[Certificate]:
        return list(self._by_group.get(group_id, []))

    def candidates(
        self, group_id: Optional[str], moment: Optional[datetime] = None
    ) -> list[Certificate]:
        """Certificados do grupo válidos no instante informado.

        Quando o grupo é desconhecido, todos os certificados são retornados —
        assim ainda é possível autenticar documentos cujo template não consta
        na base local.
        """
        certs = self.by_group(group_id) or (
            list(self._certificates) if group_id is None else []
        )
        if moment is None:
            return certs
        return [c for c in certs if c.is_valid_at(moment)]


class TemplateStore:
    """Coleção de templates (tipos de documento)."""

    def __init__(self, templates: Iterable[Template]) -> None:
        self._templates = list(templates)
        self._by_id: dict[int, Template] = {}
        for template in self._templates:
            # o JSON pode conter várias versões do mesmo id; a última vence
            self._by_id[template.id] = template

    # -- construtores ---------------------------------------------------- #
    @classmethod
    def from_json(cls, payload: list[dict]) -> "TemplateStore":
        templates = []
        for item in payload:
            valid = item.get("valid") or {}
            owner = item.get("owner") or {}
            fields = tuple(
                TemplateField(name=f.get("name"), label=f.get("label"))
                for f in (item.get("fields") or [])
            )
            templates.append(
                Template(
                    id=item.get("id"),
                    name=item.get("name"),
                    owner=owner.get("name"),
                    owner_id=owner.get("id"),
                    fields=fields,
                    certificate_group=(item.get("certificate_group") or {}).get("id"),
                    valid_from=parse_datetime(valid.get("from")),
                    valid_until=parse_datetime(valid.get("until")),
                    sandbox=bool(item.get("sandbox", False)),
                )
            )
        return cls(templates)

    @classmethod
    def from_file(cls, path: str | Path) -> "TemplateStore":
        with open(path, "r", encoding="utf-8") as handle:
            return cls.from_json(json.load(handle))

    @classmethod
    def default(cls) -> "TemplateStore":
        return cls.from_file(TEMPLATES_FILE)

    # -- consultas ------------------------------------------------------- #
    def __iter__(self) -> Iterator[Template]:
        return iter(self._templates)

    def __len__(self) -> int:
        return len(self._templates)

    def get(self, template_id: int) -> Optional[Template]:
        return self._by_id.get(template_id)


class CINKeyStore:
    """Chaves públicas (JWK) que assinam o QRCode da CIN, por ambiente.

    O app oficial usa apenas ``PROD`` (``CURRENT_ENV``); os demais ambientes
    ficam disponíveis para depuração de QRCodes de homologação.
    """

    def __init__(self, keys: Iterable[CINKey], default_id: str = "PROD") -> None:
        self._keys = list(keys)
        self._by_id = {key.id: key for key in self._keys}
        self.default_id = default_id

    # -- construtores ---------------------------------------------------- #
    @classmethod
    def from_json(cls, payload: dict) -> "CINKeyStore":
        keys = [
            CINKey(
                id=item.get("id"),
                jwk=item.get("public_key") or {},
                base_url=item.get("base_url"),
            )
            for item in (payload.get("environments") or [])
        ]
        return cls(keys, default_id=payload.get("default") or "PROD")

    @classmethod
    def from_file(cls, path: str | Path) -> "CINKeyStore":
        with open(path, "r", encoding="utf-8") as handle:
            return cls.from_json(json.load(handle))

    @classmethod
    def default(cls) -> "CINKeyStore":
        return cls.from_file(CIN_KEYS_FILE)

    # -- consultas ------------------------------------------------------- #
    def __iter__(self) -> Iterator[CINKey]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def get(self, environment: Optional[str] = None) -> Optional[CINKey]:
        return self._by_id.get(environment or self.default_id)

    def candidates(self, environment: Optional[str] = None) -> list[CINKey]:
        """Chaves a testar: só o ambiente pedido, ou todos quando ``environment`` é ``"*"``."""
        if environment == "*":
            return list(self._keys)
        key = self.get(environment)
        return [key] if key is not None else []


_DEFAULT_CERTIFICATES: Optional[CertificateStore] = None
_DEFAULT_TEMPLATES: Optional[TemplateStore] = None
_DEFAULT_CIN_KEYS: Optional[CINKeyStore] = None


def default_certificates() -> CertificateStore:
    global _DEFAULT_CERTIFICATES
    if _DEFAULT_CERTIFICATES is None:
        _DEFAULT_CERTIFICATES = CertificateStore.default()
    return _DEFAULT_CERTIFICATES


def default_templates() -> TemplateStore:
    global _DEFAULT_TEMPLATES
    if _DEFAULT_TEMPLATES is None:
        _DEFAULT_TEMPLATES = TemplateStore.default()
    return _DEFAULT_TEMPLATES


def default_cin_keys() -> CINKeyStore:
    global _DEFAULT_CIN_KEYS
    if _DEFAULT_CIN_KEYS is None:
        _DEFAULT_CIN_KEYS = CINKeyStore.default()
    return _DEFAULT_CIN_KEYS
