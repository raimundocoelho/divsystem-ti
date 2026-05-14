"""Settings (chave-valor) por tenant.

Replica a tabela `settings` do Laravel com `UNIQUE(tenant_id, key)`. Setting global
(sem tenant) é usado para configs do superadmin (ex.: master key compartilhada
para enroll de agentes).
"""
import json

from django.db import models

from apps.core.managers import AllTenantsManager
from apps.core.models import TenantOwnedModel
from apps.core.threadlocal import get_current_tenant


class Setting(TenantOwnedModel):
    """Pares chave-valor escopados por tenant.

    O valor é serializado em JSON quando não é string — `Setting.set('flags',
    {'a': 1})` → guarda `{"a": 1}` e `Setting.get('flags')` devolve dict.
    """

    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.CASCADE,
        related_name="settings",
        null=True,
        blank=True,
        db_index=True,
    )
    key = models.CharField(max_length=255)
    value = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Configuração"
        verbose_name_plural = "Configurações"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "key"], name="uq_setting_tenant_key"),
        ]
        indexes = [
            models.Index(fields=["key"]),
        ]

    def __str__(self) -> str:
        return f"{self.key}={self.value!r}"

    # --- API de uso ---------------------------------------------------------

    @classmethod
    def get(cls, key: str, default=None, tenant=None):
        tenant = tenant if tenant is not None else get_current_tenant()
        tenant_id = tenant.pk if tenant else None
        try:
            obj = cls.all_tenants.get(tenant_id=tenant_id, key=key)
        except cls.DoesNotExist:
            return default
        return cls._decode(obj.value)

    @classmethod
    def set(cls, key: str, value, tenant=None) -> "Setting":
        tenant = tenant if tenant is not None else get_current_tenant()
        tenant_id = tenant.pk if tenant else None
        encoded = cls._encode(value)
        obj, _ = cls.all_tenants.update_or_create(
            tenant_id=tenant_id, key=key, defaults={"value": encoded}
        )
        return obj

    @classmethod
    def delete_key(cls, key: str, tenant=None) -> int:
        tenant = tenant if tenant is not None else get_current_tenant()
        tenant_id = tenant.pk if tenant else None
        deleted, _ = cls.all_tenants.filter(tenant_id=tenant_id, key=key).delete()
        return deleted

    @staticmethod
    def _encode(value) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _decode(raw):
        if raw is None or raw == "":
            return raw
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return raw


class Wallpaper(TenantOwnedModel):
    """Imagem de papel de parede aplicada (ou aplicavel) aos agentes do tenant.

    Cada upload vira um registro. Aplicar = criar RemoteCommand `set_wallpaper`
    pra cada agente ativo no escopo (tenant inteiro / secretaria / setor).
    """

    secretaria = models.ForeignKey(
        "organizacoes.Secretaria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wallpapers",
        help_text="Escopo opcional — se vazio, aplica em todo o tenant.",
    )
    setor = models.ForeignKey(
        "organizacoes.Setor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wallpapers",
    )

    image_url = models.URLField(max_length=500)
    image_key = models.CharField(max_length=500, help_text="R2 object key (pra delete futuro).")
    original_filename = models.CharField(max_length=255, blank=True, default="")
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    file_size = models.PositiveIntegerField(default=0)

    uploaded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wallpapers_uploaded",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    applied_at = models.DateTimeField(null=True, blank=True)
    applied_count = models.PositiveIntegerField(
        default=0, help_text="Quantos agentes receberam o comando."
    )

    class Meta:
        verbose_name = "Papel de parede"
        verbose_name_plural = "Papeis de parede"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Wallpaper #{self.pk} ({self.original_filename or self.image_key})"

    @property
    def scope_label(self) -> str:
        parts = []
        if self.secretaria_id:
            parts.append(self.secretaria.nome if self.secretaria else f"sec#{self.secretaria_id}")
        if self.setor_id:
            parts.append(self.setor.nome if self.setor else f"setor#{self.setor_id}")
        return " > ".join(parts) if parts else "Tenant inteiro"

