"""Custom Django storage backend para Cloudflare R2 via API REST.

Usa o `CLOUDFLARE_R2_TOKEN` (formato `cfut_*`) que é o API Token global do
Cloudflare, e bate em `api.cloudflare.com/client/v4/accounts/{id}/r2/buckets/
{bucket}/objects/{key}`. Equivalente ao que o `build.bat` do agente já faz pra
publicar o `WinSysMon.exe` no bucket `divsystem-agent-updates`.

Vantagem: NÃO requer gerar Access Key ID + Secret Access Key separados — só o
API Token que o usuário já gerou. Suficiente pra read/write objetos.

Limitações vs django-storages/S3:
- Sem multipart upload (corpo inteiro é PUT direto). OK pra screenshots <10 MB.
- Sem signed URLs — assume bucket público (pub-*.r2.dev). Caso o bucket vire
  privado depois, precisamos migrar pra creds S3 + boto3.
"""
from __future__ import annotations

import logging
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

log = logging.getLogger(__name__)


@deconstructible
class CloudflareR2Storage(Storage):
    """Storage Django que persiste objetos no R2 via Cloudflare API.

    Lê configuração de `settings.py`:
        CLOUDFLARE_R2_ACCOUNT_ID
        CLOUDFLARE_R2_BUCKET
        CLOUDFLARE_R2_TOKEN  (cfut_*)
        CLOUDFLARE_R2_PUBLIC_URL  (pub-*.r2.dev — usado pra montar URLs públicas)
    """

    API_BASE = "https://api.cloudflare.com/client/v4"

    def __init__(self, account_id=None, bucket=None, token=None, public_url=None, location=""):
        self.account_id = account_id or settings.R2_ACCOUNT_ID
        self.bucket = bucket or settings.R2_BUCKET
        self.token = token or settings.R2_TOKEN
        self.public_url = (public_url or settings.R2_PUBLIC_URL or "").rstrip("/")
        self.location = (location or "").strip("/")
        if not all([self.account_id, self.bucket, self.token]):
            raise ValueError(
                "CloudflareR2Storage requer R2_ACCOUNT_ID, R2_BUCKET e R2_TOKEN."
            )

    # ─── helpers ────────────────────────────────────────────────────

    def _key(self, name: str) -> str:
        if self.location:
            return f"{self.location}/{name}"
        return name

    def _object_url(self, name: str) -> str:
        key = quote(self._key(name), safe="/")
        return f"{self.API_BASE}/accounts/{self.account_id}/r2/buckets/{self.bucket}/objects/{key}"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    # ─── Storage API ────────────────────────────────────────────────

    def _save(self, name: str, content) -> str:
        # Lê todo o stream (screenshots <10 MB, OK em memória)
        if hasattr(content, "seek"):
            try:
                content.seek(0)
            except (OSError, ValueError):
                pass
        body = content.read()
        url = self._object_url(name)
        ctype = getattr(content, "content_type", None) or "application/octet-stream"
        r = requests.put(
            url,
            data=body,
            headers={**self._headers(), "Content-Type": ctype},
            timeout=120,
        )
        if not r.ok:
            log.error("R2 PUT falhou: %s %s — %s", r.status_code, name, r.text[:200])
            r.raise_for_status()
        log.info("R2 PUT %s (%d bytes)", name, len(body))
        return name

    def _open(self, name: str, mode="rb"):
        url = self._object_url(name)
        r = requests.get(url, headers=self._headers(), timeout=120)
        r.raise_for_status()
        return ContentFile(r.content, name=name)

    def delete(self, name: str) -> None:
        url = self._object_url(name)
        try:
            r = requests.delete(url, headers=self._headers(), timeout=30)
            if r.status_code not in (200, 204, 404):
                log.warning("R2 DELETE %s -> %s", name, r.status_code)
        except requests.RequestException as e:
            log.warning("R2 DELETE falhou em %s: %s", name, e)

    def exists(self, name: str) -> bool:
        url = self._object_url(name)
        try:
            r = requests.head(url, headers=self._headers(), timeout=30)
            return r.status_code == 200
        except requests.RequestException:
            return False

    def size(self, name: str) -> int:
        url = self._object_url(name)
        try:
            r = requests.head(url, headers=self._headers(), timeout=30)
            return int(r.headers.get("Content-Length", 0))
        except requests.RequestException:
            return 0

    def url(self, name: str) -> str:
        # Bucket público em pub-*.r2.dev — URL direta, sem assinatura.
        if self.public_url:
            key = quote(self._key(name), safe="/")
            return f"{self.public_url}/{key}"
        # Fallback: a API URL (não serve pra <img src>, mas evita exception)
        return self._object_url(name)

    def get_modified_time(self, name: str):
        # Não temos esse dado via API; retornamos None para forçar fallback.
        from django.utils import timezone
        return timezone.now()
