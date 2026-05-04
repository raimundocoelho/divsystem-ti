"""Provisionamento WireGuard para equipamentos Mikrotik.

Estratégia:
- O Django gera o par de chaves do peer (a privkey vai dentro do script de
  bootstrap entregue ao Mikrotik; a pubkey é registrada no hub).
- Aloca o próximo IP livre dentro de WG_SUBNET, pulando o gateway do servidor.
- Para mexer em /etc/wireguard/wg0.conf e aplicar via `wg syncconf`, chama o
  wrapper `divsystem-wg-peer` (instalado em /usr/local/sbin) via sudo. O wrapper
  é a ÚNICA superfície privilegiada exposta ao processo Django.
"""
from __future__ import annotations

import ipaddress
import logging
import shutil
import subprocess
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction

from apps.mikrotik.models import Equipamento

logger = logging.getLogger(__name__)


WG_SUBNET = ipaddress.IPv4Network(getattr(settings, "WG_SUBNET", "10.10.10.0/24"))
WG_SERVER_IP = ipaddress.IPv4Address(getattr(settings, "WG_SERVER_IP", "10.10.10.1"))
WG_ENDPOINT_HOST = getattr(settings, "WG_ENDPOINT_HOST", "178.105.4.179")
WG_ENDPOINT_PORT = int(getattr(settings, "WG_ENDPOINT_PORT", 51820))
WG_SERVER_PUBKEY = getattr(settings, "WG_SERVER_PUBKEY", "")
WG_PEER_WRAPPER = getattr(settings, "WG_PEER_WRAPPER", "/usr/local/sbin/divsystem-wg-peer")


class WireGuardError(RuntimeError):
    pass


@dataclass(frozen=True)
class Keypair:
    private: str
    public: str


def gen_keypair() -> Keypair:
    """Gera um par de chaves WireGuard usando o binário `wg`."""
    if not shutil.which("wg"):
        raise WireGuardError("Binário 'wg' não encontrado no servidor.")
    priv = subprocess.run(
        ["wg", "genkey"], check=True, capture_output=True, text=True
    ).stdout.strip()
    pub = subprocess.run(
        ["wg", "pubkey"], input=priv, check=True, capture_output=True, text=True
    ).stdout.strip()
    return Keypair(private=priv, public=pub)


def allocate_ip(exclude: set[str] | None = None) -> str:
    """Retorna o próximo IPv4 livre em WG_SUBNET, exceto rede/broadcast/gateway."""
    used = set(
        Equipamento.all_tenants.exclude(wg_ip=None).values_list("wg_ip", flat=True)
    )
    if exclude:
        used.update(exclude)
    used.add(str(WG_SERVER_IP))

    for host in WG_SUBNET.hosts():
        ip = str(host)
        if ip not in used:
            return ip
    raise WireGuardError(f"Sem IPs livres em {WG_SUBNET}")


def _run_wrapper(*args: str, timeout: int = 15) -> subprocess.CompletedProcess:
    cmd = ["sudo", "-n", WG_PEER_WRAPPER, *args]
    try:
        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.CalledProcessError as exc:
        raise WireGuardError(
            f"Falha ao executar {' '.join(cmd)}: rc={exc.returncode} "
            f"stderr={exc.stderr!r} stdout={exc.stdout!r}"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise WireGuardError(f"Timeout em {' '.join(cmd)}") from exc
    return result


def add_peer(equipamento: Equipamento) -> None:
    """Adiciona/atualiza o peer no hub WG (idempotente)."""
    if not equipamento.wg_pubkey_device or not equipamento.wg_ip:
        raise WireGuardError("Equipamento sem chave pública ou IP atribuído.")
    _run_wrapper("add", str(equipamento.pk), equipamento.wg_pubkey_device, equipamento.wg_ip)


def remove_peer(equipamento: Equipamento) -> None:
    _run_wrapper("remove", str(equipamento.pk))


def show_status() -> str:
    """Retorna saída de `wg show wg0` para diagnóstico."""
    return _run_wrapper("list").stdout


@transaction.atomic
def provision_equipamento(equipamento: Equipamento) -> Equipamento:
    """Gera chaves, aloca IP e cadastra o peer no hub. Idempotente por (id)."""
    if not WG_SERVER_PUBKEY:
        raise WireGuardError(
            "WG_SERVER_PUBKEY não configurado em settings/.env — defina-o "
            "antes de provisionar equipamentos."
        )

    if not equipamento.wg_privkey_device or not equipamento.wg_pubkey_device:
        kp = gen_keypair()
        equipamento.wg_privkey_device = kp.private
        equipamento.wg_pubkey_device = kp.public

    if not equipamento.wg_ip:
        equipamento.wg_ip = allocate_ip()

    equipamento.wg_endpoint_host = WG_ENDPOINT_HOST
    equipamento.wg_endpoint_port = WG_ENDPOINT_PORT
    equipamento.status = "aguardando_bootstrap"
    equipamento.save()

    add_peer(equipamento)
    return equipamento
