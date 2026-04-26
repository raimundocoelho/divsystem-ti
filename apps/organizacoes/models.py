"""Secretarias e Setores — entidades organizacionais dentro de uma prefeitura.

- Secretaria → Setor é 1:N. Setor pode ser nulo na criação inicial de equipamentos.
- `codigo` permite rastreio interno (ex.: '0001'). Único por tenant.
"""
from django.db import models
from django.utils.text import slugify

from apps.core.models import TenantOwnedModel


class Secretaria(TenantOwnedModel):
    nome = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, blank=True)
    codigo = models.CharField(max_length=4, blank=True, default="")
    descricao = models.CharField(max_length=255, blank=True, default="")
    responsavel = models.CharField(max_length=100, blank=True, default="")
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Secretaria"
        verbose_name_plural = "Secretarias"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "slug"], name="uq_secretaria_tenant_slug"),
            models.UniqueConstraint(
                fields=["tenant", "codigo"],
                name="uq_secretaria_tenant_codigo",
                condition=~models.Q(codigo=""),
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "ativo"]),
        ]

    def __str__(self) -> str:
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug or self._state.adding:
            base = slugify(self.nome) or "secretaria"
            slug = base
            n = 2
            qs = Secretaria.all_tenants.filter(tenant_id=self.tenant_id, slug=slug)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            while qs.exists():
                slug = f"{base}-{n}"
                n += 1
                qs = Secretaria.all_tenants.filter(tenant_id=self.tenant_id, slug=slug)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
            self.slug = slug
        super().save(*args, **kwargs)


class Setor(TenantOwnedModel):
    secretaria = models.ForeignKey(
        Secretaria,
        on_delete=models.SET_NULL,
        related_name="setores",
        null=True,
        blank=True,
    )
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, blank=True, default="")
    responsavel = models.CharField(max_length=100, blank=True, default="")
    localizacao = models.CharField(max_length=150, blank=True, default="")
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Setor"
        verbose_name_plural = "Setores"
        ordering = ["nome"]
        db_table = "setores"
        indexes = [
            models.Index(fields=["tenant", "secretaria"]),
        ]

    def __str__(self) -> str:
        return self.nome
