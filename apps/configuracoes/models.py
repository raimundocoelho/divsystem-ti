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
