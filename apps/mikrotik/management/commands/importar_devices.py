"""Importa Devices em massa a partir de um CSV.

Uso:
    python manage.py importar_devices <equipamento_slug> <csv_path>
                                       [--dry-run] [--no-sync] [--encoding utf-8]

Colunas esperadas no CSV (header obrigatório):
    nome, mac_address, ip_address, tipo, secretaria, setor,
    responsavel, hostname, descricao

Apenas `nome` e `mac_address` são obrigatórios. `ip_address` é necessário pra
sincronizar com o router (sem ele o Device é só cadastrado no banco).

Linhas com MAC já existente no equipamento são puladas (idempotente).
Secretaria/Setor são procurados por nome (case-insensitive) dentro do tenant
do equipamento — se não existirem, a linha falha com mensagem clara.
"""
from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.mikrotik.models import Device, Equipamento
from apps.mikrotik.services import devices as devices_svc
from apps.organizacoes.models import Secretaria, Setor


REQUIRED_COLS = {"nome", "mac_address"}
OPTIONAL_COLS = {
    "ip_address", "tipo", "secretaria", "setor",
    "responsavel", "hostname", "descricao",
}
ALLOWED_TIPOS = {c[0] for c in Device.TIPO_CHOICES}


class Command(BaseCommand):
    help = "Importa Devices em massa de um CSV pra um Equipamento."

    def add_arguments(self, parser):
        parser.add_argument("equipamento_slug")
        parser.add_argument("csv_path")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Só valida e mostra o que faria, não grava nada.",
        )
        parser.add_argument(
            "--no-sync", action="store_true",
            help="Cria os Devices no banco mas não empurra static lease pro router.",
        )
        parser.add_argument(
            "--encoding", default="utf-8-sig",
            help="Encoding do CSV (default: utf-8-sig — aceita BOM do Excel).",
        )

    def handle(self, *args, **opts):
        slug = opts["equipamento_slug"]
        path = Path(opts["csv_path"])
        dry_run = opts["dry_run"]
        no_sync = opts["no_sync"]
        encoding = opts["encoding"]

        try:
            eq = Equipamento.all_tenants.get(slug=slug)
        except Equipamento.DoesNotExist:
            raise CommandError(f"Equipamento com slug '{slug}' não existe.")

        if not path.exists():
            raise CommandError(f"CSV não encontrado: {path}")

        with path.open(newline="", encoding=encoding) as fh:
            sample = fh.read(2048)
            fh.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(fh, dialect=dialect)
            rows = list(reader)
            cols = set(reader.fieldnames or [])

        missing = REQUIRED_COLS - cols
        if missing:
            raise CommandError(
                f"Colunas obrigatórias ausentes no CSV: {sorted(missing)}. "
                f"Encontrei: {sorted(cols)}"
            )

        self.stdout.write(self.style.NOTICE(
            f"Equipamento: {eq.nome} ({eq.slug}) — tenant={eq.tenant.code}"
        ))
        self.stdout.write(f"Linhas no CSV: {len(rows)}")
        self.stdout.write(f"Modo: {'DRY-RUN' if dry_run else 'EXECUTAR'}"
                          f"{' / sem sync router' if no_sync else ''}\n")

        existing_macs = set(
            Device.all_tenants
            .filter(tenant=eq.tenant, equipamento=eq)
            .values_list("mac_address", flat=True)
        )

        secretaria_cache: dict[str, Secretaria | None] = {}
        setor_cache: dict[str, Setor | None] = {}

        ok = skipped = errors = synced = sync_failed = 0

        for i, row in enumerate(rows, start=2):
            label = f"L{i}"
            try:
                nome = (row.get("nome") or "").strip()
                mac_raw = (row.get("mac_address") or "").strip()
                if not nome or not mac_raw:
                    raise ValueError("nome e mac_address são obrigatórios")

                mac = _normalize_mac(mac_raw)
                if mac in existing_macs:
                    self.stdout.write(self.style.WARNING(
                        f"  {label} skip: MAC {mac} já cadastrado ({nome})"
                    ))
                    skipped += 1
                    continue

                tipo = (row.get("tipo") or "computador").strip().lower()
                if tipo not in ALLOWED_TIPOS:
                    raise ValueError(
                        f"tipo inválido '{tipo}' (válidos: {sorted(ALLOWED_TIPOS)})"
                    )

                secretaria = _lookup_org(
                    Secretaria, row.get("secretaria"), eq.tenant_id, secretaria_cache,
                )
                setor = _lookup_org(
                    Setor, row.get("setor"), eq.tenant_id, setor_cache,
                )

                ip = (row.get("ip_address") or "").strip() or None

                device = Device(
                    tenant=eq.tenant,
                    equipamento=eq,
                    nome=nome,
                    mac_address=mac,
                    ip_address=ip,
                    tipo=tipo,
                    secretaria=secretaria,
                    setor=setor,
                    responsavel=(row.get("responsavel") or "").strip(),
                    hostname=(row.get("hostname") or "").strip(),
                    descricao=(row.get("descricao") or "").strip(),
                    status="ativo",
                )

                if dry_run:
                    self.stdout.write(self.style.SUCCESS(
                        f"  {label} OK (dry): {nome} {mac} ip={ip or '-'} "
                        f"sec={secretaria} setor={setor}"
                    ))
                    ok += 1
                    existing_macs.add(mac)
                    continue

                with transaction.atomic():
                    device.save()
                ok += 1
                existing_macs.add(mac)

                if ip and not no_sync:
                    try:
                        devices_svc.sync_device_to_router(device)
                        synced += 1
                        self.stdout.write(self.style.SUCCESS(
                            f"  {label} OK + lease: {nome} {mac} {ip}"
                        ))
                    except Exception as exc:  # noqa: BLE001
                        sync_failed += 1
                        self.stdout.write(self.style.WARNING(
                            f"  {label} OK no banco, sync FALHOU: {nome} {mac} -> {exc}"
                        ))
                else:
                    why = "sem ip" if not ip else "--no-sync"
                    self.stdout.write(self.style.SUCCESS(
                        f"  {label} OK ({why}): {nome} {mac}"
                    ))

            except Exception as exc:  # noqa: BLE001
                errors += 1
                self.stdout.write(self.style.ERROR(
                    f"  {label} ERRO: {exc} :: {dict(row)}"
                ))

        self.stdout.write("")
        summary = (
            f"Resumo: ok={ok} skipped={skipped} errors={errors}"
            f" synced={synced} sync_failed={sync_failed}"
        )
        style = self.style.SUCCESS if errors == 0 else self.style.WARNING
        self.stdout.write(style(summary))


def _normalize_mac(mac: str) -> str:
    return mac.upper().replace("-", ":").replace(".", ":").strip()


def _lookup_org(model, name: str | None, tenant_id: int, cache: dict):
    """Procura Secretaria/Setor por nome (case-insensitive) no tenant.

    Retorna None se nome vazio. Levanta ValueError se nome não encontrado.
    """
    if not name:
        return None
    key = name.strip().lower()
    if not key:
        return None
    if key in cache:
        return cache[key]
    obj = model.all_tenants.filter(tenant_id=tenant_id, nome__iexact=key).first()
    if obj is None:
        raise ValueError(
            f"{model._meta.verbose_name} '{name}' não existe no tenant"
        )
    cache[key] = obj
    return obj
