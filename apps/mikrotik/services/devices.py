"""Serviço de gestão de dispositivos: discovery + sync com o RouterOS.

Fluxo principal:
- `pull_observations(eq)` consulta DHCP/ARP/bridge no Mikrotik e:
  - cria DeviceObservation pra cada MAC visto (histórico)
  - atualiza Device.last_seen_at se o MAC já é conhecido
  - cria/atualiza RogueAlert se o MAC é desconhecido
- `sync_to_router(eq)` empurra os Devices ativos como static DHCP leases.
- `delete_lease(eq, device)` remove a static lease pro device.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from apps.mikrotik.models import (
    Device,
    DeviceObservation,
    Equipamento,
    RogueAlert,
    _normalize_mac,
)
from apps.mikrotik.services.api import RouterOSAPIError, RouterOSClient

logger = logging.getLogger(__name__)


# === marker no comment dos leases para reconhecer entradas geridas pelo painel ===
LEASE_COMMENT_PREFIX = "DIVSYSTEM:"
DEFAULT_DHCP_SERVER = "defconf"  # nome do server DHCP padrão do hEX


@dataclass
class DiscoveryResult:
    seen: dict[str, dict] = field(default_factory=dict)  # mac -> info combinada
    known: list[Device] = field(default_factory=list)
    rogues: list[RogueAlert] = field(default_factory=list)
    new_observations: int = 0


def _info_from_lease(l: dict) -> dict:
    return {
        "ip": l.get("address") or l.get("active-address"),
        "hostname": l.get("host-name", "") or "",
        "interface": "",
        "source": "dhcp",
    }


def _info_from_arp(a: dict) -> dict:
    return {
        "ip": a.get("address"),
        "hostname": "",
        "interface": a.get("interface", "") or "",
        "source": "arp",
    }


def _info_from_host(h: dict) -> dict:
    return {
        "ip": None,
        "hostname": "",
        "interface": h.get("on-interface", "") or h.get("interface", ""),
        "source": "bridge",
    }


@transaction.atomic
def pull_observations(equipamento: Equipamento) -> DiscoveryResult:
    """Lê DHCP/ARP/bridge-host e atualiza o estado de presença + rogues."""
    client = RouterOSClient(equipamento)
    result = DiscoveryResult()

    leases = client.get("/ip/dhcp-server/lease") or []
    arps = client.get("/ip/arp") or []
    hosts = client.get("/interface/bridge/host") or []

    # Combina dados das 3 fontes por MAC. Prioridade pra DHCP > ARP > bridge.
    info_by_mac: dict[str, dict] = defaultdict(dict)

    for h in hosts:
        if h.get("local") == "true":
            continue
        mac = _normalize_mac(h.get("mac-address", ""))
        if not mac:
            continue
        info_by_mac[mac].update(_info_from_host(h))
        DeviceObservation.objects.create(
            tenant=equipamento.tenant,
            equipamento=equipamento,
            mac_address=mac,
            interface=h.get("on-interface", "") or h.get("interface", ""),
            source="bridge",
        )
        result.new_observations += 1

    for a in arps:
        # ignora ARP da WAN (ether1 default)
        if a.get("interface") == "ether1":
            continue
        mac = _normalize_mac(a.get("mac-address", ""))
        if not mac:
            continue
        info_by_mac[mac].update(_info_from_arp(a))
        DeviceObservation.objects.create(
            tenant=equipamento.tenant,
            equipamento=equipamento,
            mac_address=mac,
            ip_address=a.get("address"),
            interface=a.get("interface", "") or "",
            source="arp",
        )
        result.new_observations += 1

    for l in leases:
        mac = _normalize_mac(l.get("mac-address", "") or l.get("active-mac-address", ""))
        if not mac:
            continue
        info_by_mac[mac].update(_info_from_lease(l))
        DeviceObservation.objects.create(
            tenant=equipamento.tenant,
            equipamento=equipamento,
            mac_address=mac,
            ip_address=l.get("address") or l.get("active-address"),
            hostname=l.get("host-name", ""),
            source="dhcp",
        )
        result.new_observations += 1

    result.seen = dict(info_by_mac)

    # Atualiza Device.last_seen / cria RogueAlert
    now = timezone.now()
    known_macs = set(
        Device.all_tenants.filter(
            tenant=equipamento.tenant, equipamento=equipamento
        ).values_list("mac_address", flat=True)
    )

    for mac, info in info_by_mac.items():
        if mac in known_macs:
            Device.all_tenants.filter(
                tenant=equipamento.tenant, equipamento=equipamento, mac_address=mac
            ).update(
                last_seen_at=now,
                last_seen_interface=info.get("interface", "") or "",
                hostname=info.get("hostname") or "",
            )
        else:
            rogue, created = RogueAlert.all_tenants.get_or_create(
                tenant=equipamento.tenant,
                equipamento=equipamento,
                mac_address=mac,
                defaults={
                    "primeiro_ip": info.get("ip"),
                    "primeiro_hostname": info.get("hostname", ""),
                    "primeiro_interface": info.get("interface", ""),
                    "status": "novo",
                },
            )
            if not created:
                rogue.contagem += 1
                rogue.save(update_fields=["contagem", "ultima_vez"])
            result.rogues.append(rogue)

    result.known = list(
        Device.all_tenants.filter(
            tenant=equipamento.tenant,
            equipamento=equipamento,
            mac_address__in=info_by_mac.keys(),
        )
    )
    return result


def _existing_lease_for_mac(client: RouterOSClient, mac: str) -> dict | None:
    leases = client.get("/ip/dhcp-server/lease") or []
    mac_u = _normalize_mac(mac)
    for l in leases:
        if _normalize_mac(l.get("mac-address", "")) == mac_u:
            return l
    return None


def sync_device_to_router(device: Device) -> None:
    """Garante que existe uma static DHCP lease pro Device no router.

    Se existir lease dinâmica pro mesmo MAC, ela é convertida pra estática.
    """
    if not device.ip_address:
        raise ValueError("Device sem ip_address — defina antes de sincronizar.")

    client = RouterOSClient(device.equipamento)
    existing = _existing_lease_for_mac(client, device.mac_address)

    payload = {
        "address": device.ip_address,
        "mac-address": device.mac_address,
        "server": DEFAULT_DHCP_SERVER,
        "comment": f"{LEASE_COMMENT_PREFIX}{device.pk}:{device.nome}"[:255],
    }

    try:
        if existing:
            if existing.get("dynamic") == "true":
                # Apaga a dinâmica e recria como estática (RouterOS não permite
                # converter `dynamic` em `static` via PATCH).
                client.delete(f"/ip/dhcp-server/lease/{existing['.id']}")
                client.put("/ip/dhcp-server/lease", payload)
            else:
                client.patch(f"/ip/dhcp-server/lease/{existing['.id']}", payload)
        else:
            client.put("/ip/dhcp-server/lease", payload)
        device.synced_at = timezone.now()
        device.sync_error = ""
        device.save(update_fields=["synced_at", "sync_error"])
    except RouterOSAPIError as exc:
        device.sync_error = str(exc)[:1000]
        device.save(update_fields=["sync_error"])
        raise


def delete_device_from_router(device: Device) -> None:
    """Remove a static lease do device. Não apaga o Device do banco."""
    client = RouterOSClient(device.equipamento)
    existing = _existing_lease_for_mac(client, device.mac_address)
    if existing and existing.get("dynamic") != "true":
        client.delete(f"/ip/dhcp-server/lease/{existing['.id']}")


def sync_all_to_router(equipamento: Equipamento) -> tuple[int, list[str]]:
    """Empurra todos Devices ativos. Retorna (contagem_ok, lista_erros)."""
    erros = []
    ok = 0
    devices = Device.all_tenants.filter(
        tenant=equipamento.tenant,
        equipamento=equipamento,
        status="ativo",
        ativo=True,
    )
    for d in devices:
        try:
            sync_device_to_router(d)
            ok += 1
        except (RouterOSAPIError, ValueError) as exc:
            erros.append(f"{d.nome} ({d.mac_address}): {exc}")
    return ok, erros
