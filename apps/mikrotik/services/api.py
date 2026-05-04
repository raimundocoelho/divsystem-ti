"""Cliente REST API do RouterOS v7.

Documentação: https://help.mikrotik.com/docs/display/ROS/REST+API

Usa HTTPS pelo IP WireGuard do equipamento (ex.: https://10.10.10.5/rest/...).
Como o certificado do RouterOS é tipicamente self-signed e o tráfego já vai
dentro de um túnel WG cifrado, validação TLS é desligada por padrão.
"""
from __future__ import annotations

import logging
import time
from typing import Any

import requests
from django.utils import timezone

from apps.mikrotik.models import Comando, Equipamento

logger = logging.getLogger(__name__)


class RouterOSAPIError(RuntimeError):
    pass


class RouterOSClient:
    def __init__(
        self,
        equipamento: Equipamento,
        *,
        timeout: float = 10.0,
        verify_tls: bool = False,
    ):
        if not equipamento.wg_ip:
            raise RouterOSAPIError("Equipamento sem IP WireGuard atribuído.")
        if not equipamento.api_user or not equipamento.api_password:
            raise RouterOSAPIError("Equipamento sem credenciais de API configuradas.")

        self.equipamento = equipamento
        self.base_url = equipamento.api_base_url
        self.auth = (equipamento.api_user, equipamento.api_password)
        self.timeout = timeout
        self.verify = verify_tls

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
    ) -> tuple[int, Any]:
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.base_url}{path}"
        try:
            resp = requests.request(
                method,
                url,
                json=json,
                auth=self.auth,
                timeout=self.timeout,
                verify=self.verify,
            )
        except requests.RequestException as exc:
            raise RouterOSAPIError(f"Falha de rede: {exc}") from exc

        try:
            body: Any = resp.json() if resp.content else None
        except ValueError:
            body = resp.text

        if resp.status_code >= 400:
            raise RouterOSAPIError(
                f"HTTP {resp.status_code} em {method} {path}: {body!r}"
            )
        return resp.status_code, body

    def get(self, path: str) -> Any:
        return self._request("GET", path)[1]

    def post(self, path: str, payload: Any | None = None) -> Any:
        return self._request("POST", path, json=payload)[1]

    def put(self, path: str, payload: Any | None = None) -> Any:
        return self._request("PUT", path, json=payload)[1]

    def patch(self, path: str, payload: Any | None = None) -> Any:
        return self._request("PATCH", path, json=payload)[1]

    def delete(self, path: str) -> Any:
        return self._request("DELETE", path)[1]

    def execute(self, command: str) -> Any:
        """Executa um comando arbitrário do RouterOS via /rest/execute."""
        return self.post("/execute", {"script": command})

    def ping(self) -> bool:
        """Probe rápido — retorna True se /system/identity respondeu."""
        try:
            self.get("/system/identity")
            return True
        except RouterOSAPIError:
            return False


def executar_comando(comando: Comando) -> Comando:
    """Executa um Comando persistido no DB e atualiza com a resposta."""
    comando.status = "executando"
    comando.save(update_fields=["status"])

    client = RouterOSClient(comando.equipamento)
    method_map = {
        "rest_get": ("GET", None),
        "rest_post": ("POST", comando.payload),
        "rest_put": ("PUT", comando.payload),
        "rest_patch": ("PATCH", comando.payload),
        "rest_delete": ("DELETE", None),
    }

    started = time.monotonic()
    try:
        if comando.tipo == "execute":
            body = client.execute(comando.path)
            status_code = 200
        else:
            method, payload = method_map[comando.tipo]
            status_code, body = client._request(method, comando.path, json=payload)

        comando.response_status = status_code
        comando.response_body = body if isinstance(body, (dict, list)) else {"raw": body}
        comando.status = "sucesso"
    except RouterOSAPIError as exc:
        comando.status = "erro"
        comando.erro = str(exc)
    finally:
        comando.duration_ms = int((time.monotonic() - started) * 1000)
        comando.completed_at = timezone.now()
        comando.save()

    return comando
