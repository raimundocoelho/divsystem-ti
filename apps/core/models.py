"""Modelos do núcleo: Tenant + abstrato BelongsToTenant."""
import secrets

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .managers import AllTenantsManager, TenantManager
from .threadlocal import get_current_tenant


RESERVED_SLUGS = {
    "www", "api", "admin", "app", "mail", "smtp", "ftp", "ns1", "ns2",
    "cdn", "static", "assets", "img", "dashboard", "login", "register",
    "install", "uninstall", "docs", "help", "support", "status", "blog",
}


def _generate_unique_slug(name: str) -> str:
    base = slugify(name) or "tenant"
    if base in RESERVED_SLUGS:
        base = f"{base}-org"
    candidate = base
    n = 2
    while Tenant.all_tenants.filter(slug=candidate).exists():
        candidate = f"{base}-{n}"
        n += 1
    return candidate


def _generate_tenant_code() -> str:
    while True:
        code = "TEN-" + secrets.token_hex(2).upper()
        if not Tenant.all_tenants.filter(code=code).exists():
            return code


def _generate_master_key() -> str:
    return secrets.token_hex(16)


class Tenant(models.Model):
    """Cada Tenant representa **uma prefeitura** (organização cliente).

    `code` e `master_key` são usados pelos agentes na hora do enroll. `external_code`
    é alternativo (ex.: integração externa). `active=False` desabilita login dos
    usuários daquele tenant sem apagar dados.
    """

    code = models.CharField(max_length=10, unique=True, db_index=True)
    external_code = models.CharField(max_length=64, blank=True, default="")
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    cnpj = models.CharField(max_length=18, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    contact_name = models.CharField(max_length=255, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    city = models.CharField(max_length=255, blank=True, default="")
    state = models.CharField(max_length=2, blank=True, default="")
    logo_url = models.URLField(max_length=500, blank=True, default="")
    master_key = models.CharField(max_length=64, unique=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    all_tenants = AllTenantsManager()
    objects = AllTenantsManager()

    class Meta:
        verbose_name = "Prefeitura (Tenant)"
        verbose_name_plural = "Prefeituras (Tenants)"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = _generate_tenant_code()
        if not self.master_key:
            self.master_key = _generate_master_key()
        if not self.slug:
            self.slug = _generate_unique_slug(self.name)
        super().save(*args, **kwargs)

    @classmethod
    def generate_code(cls) -> str:
        return _generate_tenant_code()

    @classmethod
    def generate_master_key(cls) -> str:
        return _generate_master_key()


class BelongsToTenantQuerySet(models.QuerySet):
    """Herda comportamento útil em querysets de modelos tenant-scoped."""

    def for_tenant(self, tenant):
        if tenant is None:
            return self.none()
        return self.filter(tenant=tenant)


class TenantScopedManager(TenantManager):
    """Manager auto-tenant que retorna `BelongsToTenantQuerySet`."""

    def get_queryset(self) -> BelongsToTenantQuerySet:
        qs = BelongsToTenantQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        if tenant is not None:
            qs = qs.filter(tenant_id=tenant.pk)
        return qs


class TenantOwnedModel(models.Model):
    """Mixin abstrato para modelos com `tenant_id`.

    - Em `save()`: se `tenant_id` está vazio, usa o tenant ativo do thread-local.
    - `objects`: filtra automaticamente pelo tenant ativo.
    - `all_tenants`: retorna registros de todos os tenants (admin/jobs).
    """

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="%(class)ss",
        db_index=True,
    )

    objects = TenantScopedManager()
    all_tenants = AllTenantsManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.tenant_id:
            current = get_current_tenant()
            if current is not None:
                self.tenant_id = current.pk
        super().save(*args, **kwargs)
