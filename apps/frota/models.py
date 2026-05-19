"""Modelos do módulo Frota — porte 1:1 do Laravel divsystem-app.

- Veiculo: cadastro do veículo (placa, modelo, capacidade, RENAVAM, chassi)
- DiarioBordo: registro de cada saída/retorno de veículo
- ManutencaoTipo: tipos pré-cadastrados de manutenção (com checklist)
- RegistroHoras: apontamento de horas trabalhadas (técnicos/TI)
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import TenantOwnedModel


class Veiculo(TenantOwnedModel):
    secretaria = models.ForeignKey(
        "organizacoes.Secretaria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="veiculos",
    )
    nome = models.CharField(max_length=100, blank=True, default="")
    placa = models.CharField(max_length=10)
    modelo = models.CharField(max_length=100)
    renavam = models.CharField(max_length=11, blank=True, default="")
    chassi = models.CharField(max_length=17, blank=True, default="")
    capacidade_passageiros = models.PositiveSmallIntegerField(null=True, blank=True)
    observacoes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Veículo"
        verbose_name_plural = "Veículos"
        ordering = ["placa"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "placa"], name="uq_veiculo_tenant_placa"),
            models.UniqueConstraint(
                fields=["tenant", "renavam"],
                name="uq_veiculo_tenant_renavam",
                condition=~models.Q(renavam=""),
            ),
            models.UniqueConstraint(
                fields=["tenant", "chassi"],
                name="uq_veiculo_tenant_chassi",
                condition=~models.Q(chassi=""),
            ),
        ]
        indexes = [models.Index(fields=["tenant", "secretaria"])]

    def __str__(self) -> str:
        if self.nome:
            return f"{self.placa} — {self.nome}"
        return f"{self.placa} {self.modelo}"


class ManutencaoTipo(TenantOwnedModel):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True, default="")
    intervalo_dias = models.PositiveIntegerField()
    duracao_estimada_minutos = models.PositiveIntegerField(default=60)
    checklist = models.JSONField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tipo de Manutenção"
        verbose_name_plural = "Tipos de Manutenção"
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class DiarioBordo(TenantOwnedModel):
    """Registro de saída/retorno de veículo (com odômetro)."""

    veiculo = models.ForeignKey(
        Veiculo,
        on_delete=models.PROTECT,
        related_name="diarios_bordo",
    )
    condutor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="diarios_bordo_condutor",
    )
    autorizador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="diarios_bordo_autorizador",
    )
    # Motorista da entidade Transporte (uso opcional — diários via app móvel).
    motorista = models.ForeignKey(
        "transporte.Motorista",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="diarios_bordo",
    )
    # Vínculo com viagem do módulo Transporte (quando o diário é gerado a partir de uma viagem SIM Saúde).
    viagem_transporte = models.ForeignKey(
        "transporte.ViagemTransporte",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="diarios_bordo",
    )

    saida_em = models.DateTimeField()
    retorno_em = models.DateTimeField(null=True, blank=True)
    km_saida = models.PositiveIntegerField()
    km_retorno = models.PositiveIntegerField(null=True, blank=True)
    destino = models.CharField(max_length=255)
    finalidade = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Diário de Bordo"
        verbose_name_plural = "Diários de Bordo"
        ordering = ["-saida_em"]
        indexes = [
            models.Index(fields=["tenant", "veiculo"]),
            models.Index(fields=["tenant", "condutor"]),
            models.Index(fields=["saida_em"]),
            models.Index(fields=["motorista"]),
            models.Index(fields=["viagem_transporte"]),
        ]

    def __str__(self) -> str:
        return f"DB#{self.pk} {self.veiculo_id} {self.saida_em:%d/%m/%Y}"


class RegistroHoras(models.Model):
    """Apontamento de horas (módulo Horas - não usa tenant)."""

    data = models.DateField()
    entrada_manha = models.TimeField(null=True, blank=True)
    saida_manha = models.TimeField(null=True, blank=True)
    entrada_tarde = models.TimeField(null=True, blank=True)
    saida_tarde = models.TimeField(null=True, blank=True)
    total_horas = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    tipo_atividade = models.CharField(max_length=100, blank=True, default="")
    competencia = models.CharField(max_length=7)  # YYYY-MM
    observacao = models.TextField(blank=True, default="")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registros_horas",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Registro de Horas"
        verbose_name_plural = "Registros de Horas"
        ordering = ["-data"]

    def __str__(self) -> str:
        return f"{self.user_id or '?'} — {self.data} ({self.total_horas or 0}h)"
