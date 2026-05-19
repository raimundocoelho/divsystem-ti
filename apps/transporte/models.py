"""Modelos do módulo Transporte — porte 1:1 do Laravel divsystem-app.

Cadastros auxiliares: CidadeDestino, LocalAtendimento, LocalEmbarque, HorarioTransporte
Entidades principais: Paciente, Motorista, ViagemTransporte, PassageiroViagem, ProtocoloExame

Fluxo SIM Saúde:
    Viagem agendada → motorista designado → passageiros embarcam → veículo
    sai → exames feitos → protocolos cadastrados → próxima viagem retira.
"""
from __future__ import annotations

import secrets

from django.conf import settings
from django.db import models

from apps.core.models import TenantOwnedModel


# ---------------------------------------------------------------------------
# Cadastros auxiliares
# ---------------------------------------------------------------------------

class CidadeDestino(TenantOwnedModel):
    nome = models.CharField(max_length=120)
    uf = models.CharField(max_length=2)
    observacao = models.CharField(max_length=255, blank=True, default="")
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cidade-Destino"
        verbose_name_plural = "Cidades-Destino"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "nome", "uf"], name="uq_cidade_dest_tenant_nome_uf"
            ),
        ]
        indexes = [models.Index(fields=["tenant", "ativo"])]

    def __str__(self) -> str:
        return f"{self.nome}/{self.uf}"


class LocalAtendimento(TenantOwnedModel):
    cidade_destino = models.ForeignKey(
        CidadeDestino,
        on_delete=models.PROTECT,
        related_name="locais_atendimento",
    )
    nome = models.CharField(max_length=160)
    endereco = models.CharField(max_length=255, blank=True, default="")
    telefone = models.CharField(max_length=30, blank=True, default="")
    observacao = models.CharField(max_length=255, blank=True, default="")
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Local de Atendimento"
        verbose_name_plural = "Locais de Atendimento"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "cidade_destino", "nome"],
                name="uq_local_atend_tenant_cidade_nome",
            ),
        ]
        indexes = [models.Index(fields=["tenant", "ativo"])]

    def __str__(self) -> str:
        return self.nome


class LocalEmbarque(TenantOwnedModel):
    nome = models.CharField(max_length=120)
    endereco = models.CharField(max_length=255, blank=True, default="")
    hora = models.TimeField(null=True, blank=True)
    observacao = models.CharField(max_length=255, blank=True, default="")
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Local de Embarque"
        verbose_name_plural = "Locais de Embarque"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "nome"], name="uq_local_emb_tenant_nome"),
        ]
        indexes = [models.Index(fields=["tenant", "ativo"])]

    def __str__(self) -> str:
        return self.nome


class HorarioTransporte(TenantOwnedModel):
    """Preset rápido de horário sugerido (ex: 05:30 — Madrugada)."""

    hora = models.TimeField()
    descricao = models.CharField(max_length=60, blank=True, default="")
    ordem = models.PositiveIntegerField(default=0)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Horário Sugerido"
        verbose_name_plural = "Horários Sugeridos"
        ordering = ["ordem", "hora"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "hora"], name="uq_horario_tenant_hora"),
        ]
        indexes = [models.Index(fields=["tenant", "ativo", "ordem"])]

    def __str__(self) -> str:
        if self.descricao:
            return f"{self.hora:%H:%M} — {self.descricao}"
        return f"{self.hora:%H:%M}"


# ---------------------------------------------------------------------------
# Paciente
# ---------------------------------------------------------------------------

class Paciente(TenantOwnedModel):
    secretaria = models.ForeignKey(
        "organizacoes.Secretaria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pacientes",
    )
    nome = models.CharField(max_length=160)
    cpf = models.CharField(max_length=14, blank=True, default="")
    cns = models.CharField(max_length=15, blank=True, default="")
    cds_individual = models.CharField(max_length=80, blank=True, default="")  # e-SUS PEC dedup
    telefone = models.CharField(max_length=30, blank=True, default="")
    data_nascimento = models.DateField(null=True, blank=True)
    sexo = models.CharField(max_length=1, blank=True, default="")
    endereco = models.CharField(max_length=255, blank=True, default="")
    bairro = models.CharField(max_length=120, blank=True, default="")
    observacao = models.TextField(blank=True, default="")
    unidade = models.CharField(max_length=160, blank=True, default="")
    equipe = models.CharField(max_length=120, blank=True, default="")
    microarea = models.CharField(max_length=20, blank=True, default="")
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "cpf"],
                name="uq_paciente_tenant_cpf",
                condition=~models.Q(cpf=""),
            ),
            models.UniqueConstraint(
                fields=["tenant", "cns"],
                name="uq_paciente_tenant_cns",
                condition=~models.Q(cns=""),
            ),
            models.UniqueConstraint(
                fields=["tenant", "cds_individual"],
                name="uq_paciente_tenant_cds",
                condition=~models.Q(cds_individual=""),
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "nome"]),
            models.Index(fields=["tenant", "ativo"]),
            models.Index(fields=["tenant", "unidade"]),
        ]

    def __str__(self) -> str:
        return self.nome


# ---------------------------------------------------------------------------
# Motorista
# ---------------------------------------------------------------------------

class Motorista(TenantOwnedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="motorista_profile",
    )
    nome = models.CharField(max_length=160)
    cpf = models.CharField(max_length=14, blank=True, default="")
    cnh = models.CharField(max_length=20)
    cnh_categoria = models.CharField(max_length=5)
    cnh_validade = models.DateField()
    telefone = models.CharField(max_length=30, blank=True, default="")
    observacao = models.TextField(blank=True, default="")
    ativo = models.BooleanField(default=True)
    access_token = models.CharField(max_length=32, blank=True, default="", db_index=True)  # link mágico
    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Motorista"
        verbose_name_plural = "Motoristas"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "cpf"],
                name="uq_motorista_tenant_cpf",
                condition=~models.Q(cpf=""),
            ),
            models.UniqueConstraint(fields=["tenant", "cnh"], name="uq_motorista_tenant_cnh"),
        ]
        indexes = [
            models.Index(fields=["tenant", "ativo"]),
            models.Index(fields=["cnh_validade"]),
        ]

    def __str__(self) -> str:
        return f"{self.nome} (CNH {self.cnh_categoria})"

    def save(self, *args, **kwargs):
        if not self.access_token:
            self.access_token = secrets.token_urlsafe(24)[:32]
        super().save(*args, **kwargs)


# ---------------------------------------------------------------------------
# Viagem
# ---------------------------------------------------------------------------

class ViagemTransporte(TenantOwnedModel):
    TIPO_CHOICES = [
        ("sim_saude", "SIM Saúde"),
        ("outro", "Outro"),
    ]
    STATUS_CHOICES = [
        ("agendada", "Agendada"),
        ("em_andamento", "Em andamento"),
        ("concluida", "Concluída"),
        ("cancelada", "Cancelada"),
    ]

    veiculo = models.ForeignKey(
        "frota.Veiculo",
        on_delete=models.PROTECT,
        related_name="viagens_transporte",
    )
    motorista = models.ForeignKey(
        Motorista,
        on_delete=models.PROTECT,
        related_name="viagens_transporte",
    )
    cidade_destino = models.ForeignKey(
        CidadeDestino,
        on_delete=models.PROTECT,
        related_name="viagens",
    )
    horario = models.ForeignKey(
        HorarioTransporte,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="viagens",
    )
    data = models.DateField()
    hora_saida = models.TimeField(null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="sim_saude")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="agendada")
    observacoes = models.TextField(blank=True, default="")
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="viagens_transporte_criadas",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Viagem de Transporte"
        verbose_name_plural = "Viagens de Transporte"
        ordering = ["-data", "-hora_saida"]
        indexes = [
            models.Index(fields=["tenant", "data", "status"]),
            models.Index(fields=["tenant", "motorista", "data"]),
            models.Index(fields=["tenant", "veiculo", "data"]),
        ]

    def __str__(self) -> str:
        return f"V#{self.pk} {self.data:%d/%m/%Y} → {self.cidade_destino.nome}"


class PassageiroViagem(models.Model):
    viagem = models.ForeignKey(
        ViagemTransporte,
        on_delete=models.CASCADE,
        related_name="passageiros",
    )
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name="passageiro_viagens",
    )
    acompanhante = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="acompanhante_viagens",
    )
    local_atendimento = models.ForeignKey(
        LocalAtendimento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="passageiros_viagem",
    )
    local_embarque = models.ForeignKey(
        LocalEmbarque,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="passageiros_viagem",
    )
    finalidade = models.CharField(max_length=200)
    presente = models.BooleanField(null=True, blank=True)
    embarcou_em = models.DateTimeField(null=True, blank=True)
    check_in_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="passageiros_check_in",
    )
    observacao = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Passageiro de Viagem"
        verbose_name_plural = "Passageiros de Viagem"
        ordering = ["viagem_id", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["viagem", "paciente"], name="uq_passageiro_viagem_paciente"
            ),
        ]
        indexes = [models.Index(fields=["paciente"])]

    def __str__(self) -> str:
        return f"{self.paciente_id} em V#{self.viagem_id}"


# ---------------------------------------------------------------------------
# Protocolo de Exame
# ---------------------------------------------------------------------------

class ProtocoloExame(TenantOwnedModel):
    TIPO_CHOICES = [
        ("exame", "Exame"),
        ("laudo", "Laudo"),
        ("receita", "Receita"),
        ("atestado", "Atestado"),
        ("outros", "Outros"),
    ]
    STATUS_CHOICES = [
        ("aguardando_retirada", "Aguardando Retirada"),
        ("aguardando_entrega", "Aguardando Entrega"),
        ("entregue", "Entregue"),
        ("cancelado", "Cancelado"),
    ]

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name="protocolos_exame",
    )
    viagem_origem = models.ForeignKey(
        ViagemTransporte,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocolos_origem",
    )
    viagem_retirada = models.ForeignKey(
        ViagemTransporte,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocolos_retirada",
    )
    local_atendimento = models.ForeignKey(
        LocalAtendimento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocolos_exame",
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default="exame")
    descricao = models.CharField(max_length=200)
    numero_protocolo = models.CharField(max_length=80, blank=True, default="")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="aguardando_retirada")
    previsao_retirada = models.DateField(null=True, blank=True)
    retirado_em = models.DateTimeField(null=True, blank=True)
    retirado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocolos_retirados",
    )
    entregue_em = models.DateTimeField(null=True, blank=True)
    entregue_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocolos_entregues",
    )
    entregue_para = models.CharField(max_length=160, blank=True, default="")
    observacoes = models.TextField(blank=True, default="")
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="protocolos_criados",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Protocolo de Exame"
        verbose_name_plural = "Protocolos de Exame"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "paciente"]),
            models.Index(fields=["tenant", "previsao_retirada"]),
            models.Index(fields=["viagem_retirada"]),
        ]

    def __str__(self) -> str:
        return f"PE#{self.pk} {self.tipo} {self.descricao}"
