"""QuerySet/Manager que aplicam o filtro `tenant_id = atual` automaticamente.

Espelha o `TenantScope` global do Laravel: o filtro corre em todo lugar, exceto
quando explicitamente desligado com `Model.all_tenants.all()`.
"""
from django.db import models

from .threadlocal import get_current_tenant


class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        if tenant is None:
            return self.none()
        tenant_id = tenant.pk if hasattr(tenant, "pk") else tenant
        return self.filter(tenant_id=tenant_id)


class TenantManager(models.Manager):
    """Manager que filtra automaticamente pelo tenant ativo (thread-local).

    Comportamento:
      - se há tenant ativo → filtra por `tenant_id`.
      - se não há tenant ativo (ex.: shell, comando management) → retorna todos.
        É deliberado: scripts administrativos costumam querer ver tudo.
    """

    use_for_related_fields = True

    def get_queryset(self) -> TenantQuerySet:
        qs = TenantQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        if tenant is not None:
            qs = qs.filter(tenant_id=tenant.pk)
        return qs


class AllTenantsManager(models.Manager):
    """Acessa registros de todos os tenants — usado em jobs cross-tenant e admin."""

    def get_queryset(self) -> TenantQuerySet:
        return TenantQuerySet(self.model, using=self._db)
