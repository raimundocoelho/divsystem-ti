"""Compilação e aplicação de Políticas de filtro web no RouterOS.

Modelo de aplicação:

- DNS sinkhole via CNAME (camada base, *afeta todos os clientes do resolver
  da hEX*): cada `RegraDominio` vira CNAME -> `BLOCK_PAGE_DOMAIN` em
  `/ip/dns/static`:
    - `name=dominio.tld` (apex)
    - se `incluir_subdominios=True`, segunda entrada com
      `regexp=^.*\\.dominio\\.tld$` cobrindo subdomínios.
  Resultado: HTTP cai na landing bonita do proxy.divsystem.com.br;
  HTTPS dá erro de cert (cert mismatch) — limitação intrínseca de DNS-based
  blocking sem TLS-interception. Por isso a camada firewall abaixo.

- Firewall TLS-SNI (granular por device, pega HTTPS antes do cert error):
  Cada par (alvo, regra) vira uma regra em `/ip/firewall/filter`:
    chain=forward, src-mac-address=<alvo.mac>, tls-host=*<dominio>*,
    protocol=tcp, dst-port=443, action=drop.
  Pega quem usa DNS externo (DoH, 8.8.8.8 hardcoded). Browser vê
  "esta página não pode ser acessada" — mais limpo que cert error.

Marcadores nos comments pra reconhecer entradas geridas pelo painel:
  - DNS:        `DIVSYSTEM:POLDNS:<politica_pk>:<regra_pk>:<dominio>`
  - Firewall:   `DIVSYSTEM:POLFW:<politica_pk>:<regra_pk>:<alvo_pk>:<dominio>`
"""
from __future__ import annotations

import logging
import re

from django.db import transaction
from django.utils import timezone

from apps.mikrotik.models import Politica, RegraDominio, PoliticaAlvo
from apps.mikrotik.services.api import RouterOSAPIError, RouterOSClient

logger = logging.getLogger(__name__)


DNS_COMMENT_PREFIX = "DIVSYSTEM:POLDNS:"
FW_COMMENT_PREFIX = "DIVSYSTEM:POLFW:"

# Domínio Cloudflare-hosted que renderiza a landing "Acesso Bloqueado".
# Pode ser tornado configurável por tenant via Tenant.block_page_domain no futuro.
BLOCK_PAGE_DOMAIN = "proxy.divsystem.com.br"


def _dns_comment(politica_pk: int, regra_pk: int, dominio: str) -> str:
    return f"{DNS_COMMENT_PREFIX}{politica_pk}:{regra_pk}:{dominio}"[:255]


def _fw_comment(politica_pk: int, regra_pk: int, alvo_pk: int, dominio: str) -> str:
    return f"{FW_COMMENT_PREFIX}{politica_pk}:{regra_pk}:{alvo_pk}:{dominio}"[:255]


def _regexp_for_subdomain(dominio: str) -> str:
    """Regexp RouterOS-compatível pra casar subdomínios. Não casa o apex.

    Mikrotik usa POSIX BRE/ERE; pra DNS static `regexp`, expressão padrão.
    Ex.: facebook.com -> `^.*\\.facebook\\.com$`
    """
    escaped = re.escape(dominio)
    return f"^.*\\.{escaped}$"


def compilar_dns_entries(politica: Politica) -> list[dict]:
    """Lista de payloads `/ip/dns/static` que esta política exige.

    Usa CNAME -> BLOCK_PAGE_DOMAIN pra que requisições HTTP caiam na landing
    do proxy.divsystem.com.br. HTTPS continua dando cert error (gatekeeping
    real é feito pelo firewall TLS-SNI).
    """
    out: list[dict] = []
    for regra in politica.regras.all():
        d = regra.dominio
        out.append({
            "name": d,
            "cname": BLOCK_PAGE_DOMAIN,
            "comment": _dns_comment(politica.pk, regra.pk, d),
        })
        if regra.incluir_subdominios:
            out.append({
                "regexp": _regexp_for_subdomain(d),
                "cname": BLOCK_PAGE_DOMAIN,
                "comment": _dns_comment(politica.pk, regra.pk, f"*.{d}"),
            })
    return out


def compilar_fw_entries(politica: Politica) -> list[dict]:
    """Lista de payloads `/ip/firewall/filter` que esta política exige.

    Quando `is_global=True`, política só usa DNS sinkhole — não cria regras
    firewall por src-mac (afeta todos os clientes do hEX via DNS).
    """
    out: list[dict] = []
    if politica.is_global:
        return out
    alvos = list(politica.alvos.select_related("device").all())
    regras = list(politica.regras.all())
    for alvo in alvos:
        mac = alvo.device.mac_address
        for regra in regras:
            d = regra.dominio
            # tls-host com wildcard pega o dominio + subdominios pelo SNI
            tls_pattern = f"*{d}*" if regra.incluir_subdominios else f"*{d}"
            out.append({
                "chain": "forward",
                "action": "drop",
                "src-mac-address": mac,
                "tls-host": tls_pattern,
                "protocol": "tcp",
                "dst-port": "443",
                "comment": _fw_comment(politica.pk, regra.pk, alvo.pk, d),
            })
    return out


def _existing_managed_entries(client: RouterOSClient, path: str, prefix: str) -> list[dict]:
    """Lê todas as entradas em `path` cujo comment começa com `prefix`."""
    items = client.get(path) or []
    return [it for it in items if (it.get("comment") or "").startswith(prefix)]


def _entries_for_politica(items: list[dict], politica_pk: int) -> list[dict]:
    """Filtra entradas managed que pertencem a uma Politica específica.

    O comment tem formato `<PREFIX><politica_pk>:...` — basta checar o int após
    o prefixo.
    """
    out: list[dict] = []
    for it in items:
        c = it.get("comment") or ""
        # Remove prefixo (já filtrado antes), pega o primeiro campo
        for prefix in (DNS_COMMENT_PREFIX, FW_COMMENT_PREFIX):
            if c.startswith(prefix):
                rest = c[len(prefix):]
                pk_str = rest.split(":", 1)[0]
                if pk_str.isdigit() and int(pk_str) == politica_pk:
                    out.append(it)
                break
    return out


@transaction.atomic
def aplicar_politica(politica: Politica) -> tuple[int, int]:
    """Empurra a política pro RouterOS.

    Estratégia: sweep-and-rebuild. Apaga TODAS as entradas managed dessa política
    no router, depois cria as novas. Garante consistência mesmo se a política foi
    editada.

    Retorna: (n_dns_criadas, n_fw_criadas)
    """
    if not politica.ativo:
        raise ValueError("Política está inativa — não pode ser aplicada.")

    client = RouterOSClient(politica.equipamento)

    # 1. Sweep antigas
    dns_existing = _existing_managed_entries(client, "/ip/dns/static", DNS_COMMENT_PREFIX)
    fw_existing = _existing_managed_entries(client, "/ip/firewall/filter", FW_COMMENT_PREFIX)
    for it in _entries_for_politica(dns_existing, politica.pk):
        client.delete(f"/ip/dns/static/{it['.id']}")
    for it in _entries_for_politica(fw_existing, politica.pk):
        client.delete(f"/ip/firewall/filter/{it['.id']}")

    # 2. Compila e cria
    dns_new = compilar_dns_entries(politica)
    fw_new = compilar_fw_entries(politica)
    try:
        for payload in dns_new:
            client.put("/ip/dns/static", payload)
        for payload in fw_new:
            client.put("/ip/firewall/filter", payload)
    except RouterOSAPIError as exc:
        politica.aplicada_erro = str(exc)[:1000]
        politica.save(update_fields=["aplicada_erro"])
        raise

    politica.aplicada_em = timezone.now()
    politica.aplicada_erro = ""
    politica.save(update_fields=["aplicada_em", "aplicada_erro"])
    return len(dns_new), len(fw_new)


def remover_politica(politica: Politica) -> tuple[int, int]:
    """Apaga as entradas dessa política no router. Não apaga a Política do banco.

    Retorna: (n_dns_apagadas, n_fw_apagadas)
    """
    client = RouterOSClient(politica.equipamento)
    dns_existing = _existing_managed_entries(client, "/ip/dns/static", DNS_COMMENT_PREFIX)
    fw_existing = _existing_managed_entries(client, "/ip/firewall/filter", FW_COMMENT_PREFIX)
    n_dns = n_fw = 0
    for it in _entries_for_politica(dns_existing, politica.pk):
        client.delete(f"/ip/dns/static/{it['.id']}")
        n_dns += 1
    for it in _entries_for_politica(fw_existing, politica.pk):
        client.delete(f"/ip/firewall/filter/{it['.id']}")
        n_fw += 1

    politica.aplicada_em = None
    politica.save(update_fields=["aplicada_em"])
    return n_dns, n_fw
