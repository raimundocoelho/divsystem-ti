"""Cria dados de demonstração para acelerar o desenvolvimento.

Uso:
    python manage.py seed_demo
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.agentes.models import AgentToken
from apps.configuracoes.models import Setting
from apps.core.models import Tenant
from apps.core.permissions import UserRole
from apps.core.threadlocal import use_tenant
from apps.organizacoes.models import Secretaria, Setor


class Command(BaseCommand):
    help = "Cria tenant, usuários, secretarias, setores e agente de exemplo."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        # Tenant principal — Divinésia
        tenant, created = Tenant.all_tenants.get_or_create(
            name="Prefeitura de Divinésia",
            defaults={
                "cnpj": "18.575.499/0001-30",
                "city": "Divinésia",
                "state": "MG",
                "email": "ti@divinesia.mg.gov.br",
                "contact_name": "Coordenadoria de TI",
                "active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"{'Criado' if created else 'Existia'} tenant: {tenant.name} ({tenant.code})"
        ))

        # Admin global
        admin, _ = User.objects.update_or_create(
            email="admin@divsystem.com.br",
            defaults={
                "name": "Suporte SABIO",
                "role": UserRole.ADMIN,
                "is_global_admin": True,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        admin.set_password("divsystem2026")
        admin.save()
        self.stdout.write(self.style.SUCCESS("Admin global: admin@divsystem.com.br / divsystem2026"))

        # Gestor da prefeitura
        gestor, _ = User.objects.update_or_create(
            email="gestor@divinesia.mg.gov.br",
            defaults={
                "name": "Gestor TI Divinésia",
                "role": UserRole.GESTOR,
                "tenant": tenant,
                "is_active": True,
            },
        )
        gestor.set_password("divsystem2026")
        gestor.save()
        self.stdout.write(self.style.SUCCESS("Gestor: gestor@divinesia.mg.gov.br / divsystem2026"))

        # Secretarias e setores
        with use_tenant(tenant):
            saude, _ = Secretaria.all_tenants.update_or_create(
                tenant=tenant, slug="secretaria-de-saude",
                defaults={"nome": "Secretaria de Saúde", "codigo": "0001", "ativo": True,
                         "responsavel": "Dra. Helena Souza"},
            )
            educacao, _ = Secretaria.all_tenants.update_or_create(
                tenant=tenant, slug="secretaria-de-educacao",
                defaults={"nome": "Secretaria de Educação", "codigo": "0002", "ativo": True,
                         "responsavel": "Prof. Carlos Lima"},
            )
            adm, _ = Secretaria.all_tenants.update_or_create(
                tenant=tenant, slug="secretaria-de-administracao",
                defaults={"nome": "Secretaria de Administração", "codigo": "0003", "ativo": True},
            )

            for sec, nomes in [
                (saude, ["PSF Vila Nova", "Hospital Municipal", "Vigilância Sanitária"]),
                (educacao, ["Escola Municipal Centro", "Creche Bem-Te-Vi"]),
                (adm, ["Recursos Humanos", "Tesouraria", "TI Central"]),
            ]:
                for nome in nomes:
                    Setor.all_tenants.update_or_create(
                        tenant=tenant, secretaria=sec, nome=nome,
                        defaults={"ativo": True},
                    )

            # Setting global e por tenant
            Setting.set("agent_master_key", "demo-master-key-2026", tenant=None)
            Setting.set(
                "blocked_sites",
                ["facebook.com", "youtube.com"],
                tenant=tenant,
            )

            # Um agente exemplo
            AgentToken.all_tenants.update_or_create(
                tenant=tenant, name="Demo TI Central",
                defaults={
                    "hostname": "ADM-TI-PC01",
                    "machine_id": "DEMO-HWID-0001",
                    "agent_version": "5.2.0",
                    "active": True,
                },
            )

        self.stdout.write(self.style.SUCCESS("Seed concluído."))
