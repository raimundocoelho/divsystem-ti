"""Modelos do módulo Patrimônio — porte 1:1 do Laravel divsystem-app.

Hierarquia:
    PatrimonioCategoria (MCASP/PCASP)
    PatrimonioLocal     (prédio → andar → sala)
    Patrimonio          (bem em si, FK em categoria + local + secretaria + setor)
        ├── PatrimonioFoto      (várias)
        ├── PatrimonioQrCode    (uma — 1:1 com bem)
        └── PatrimonioDepreciacao  (snapshot mensal pra RABM)
    PatrimonioCadastroIa  (log/audit de cadastros via IA Vision)
"""
from __future__ import annotations

import random

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TenantOwnedModel


# ---------------------------------------------------------------------------
# Categoria MCASP / PCASP
# ---------------------------------------------------------------------------

class PatrimonioCategoria(TenantOwnedModel):
    """Categoria contábil MCASP/PCASP.

    Categorias com tenant=None são globais (seed da STN, compartilhadas).
    """

    METODO_CHOICES = [
        ("linear", "Linear"),
        ("saldos_decrescentes", "Saldos Decrescentes"),
        ("unidades_produzidas", "Unidades Produzidas"),
    ]

    nome = models.CharField(max_length=120)
    codigo_mcasp = models.CharField(max_length=30, blank=True, default="")
    nome_conta_pcasp = models.CharField(max_length=200, blank=True, default="")
    vida_util_anos = models.PositiveSmallIntegerField(null=True, blank=True)
    taxa_depreciacao_anual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    valor_residual_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    metodo_depreciacao = models.CharField(max_length=30, choices=METODO_CHOICES, default="linear")
    deprecia = models.BooleanField(default=True)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Categoria de Patrimônio"
        verbose_name_plural = "Categorias de Patrimônio"
        ordering = ["nome"]
        indexes = [models.Index(fields=["tenant", "ativo"])]

    def __str__(self) -> str:
        return f"{self.codigo_mcasp} {self.nome}".strip()

    @property
    def conta_formatada(self) -> str:
        """Conta PCASP formatada com pontos (ex: 1.2.3.1.1.05.00)."""
        if not self.codigo_mcasp:
            return ""
        digits = "".join(c for c in self.codigo_mcasp if c.isdigit())
        if len(digits) < 5:
            return self.codigo_mcasp
        partes = list(digits[:5])
        resto = digits[5:]
        for i in range(0, len(resto), 2):
            partes.append(resto[i:i + 2])
        return ".".join(partes)


# ---------------------------------------------------------------------------
# Local físico (hierárquico)
# ---------------------------------------------------------------------------

class PatrimonioLocal(TenantOwnedModel):
    TIPO_CHOICES = [
        ("predio", "Prédio"),
        ("andar", "Andar"),
        ("sala", "Sala"),
        ("outro", "Outro"),
    ]

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )
    secretaria = models.ForeignKey(
        "organizacoes.Secretaria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patrimonio_locais",
    )
    setor = models.ForeignKey(
        "organizacoes.Setor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patrimonio_locais",
    )
    nome = models.CharField(max_length=120)
    tipo = models.CharField(max_length=8, choices=TIPO_CHOICES, default="sala")
    endereco = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Local Patrimonial"
        verbose_name_plural = "Locais Patrimoniais"
        ordering = ["nome"]
        indexes = [
            models.Index(fields=["secretaria", "setor"]),
            models.Index(fields=["tenant", "parent"]),
        ]

    def __str__(self) -> str:
        return self.nome


# ---------------------------------------------------------------------------
# Bem patrimonial
# ---------------------------------------------------------------------------

class Patrimonio(TenantOwnedModel):
    ESTADO_CHOICES = [
        ("novo", "Novo"),
        ("bom", "Bom"),
        ("regular", "Regular"),
        ("ruim", "Ruim"),
        ("inservivel", "Inservível"),
    ]
    SITUACAO_CHOICES = [
        ("ativo", "Ativo"),
        ("em_manutencao", "Em Manutenção"),
        ("baixado", "Baixado"),
        ("transferido", "Transferido"),
        ("emprestado", "Emprestado"),
    ]

    secretaria = models.ForeignKey(
        "organizacoes.Secretaria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patrimonios",
    )
    setor = models.ForeignKey(
        "organizacoes.Setor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patrimonios",
    )
    categoria = models.ForeignKey(
        PatrimonioCategoria,
        on_delete=models.PROTECT,
        related_name="patrimonios",
    )
    local = models.ForeignKey(
        PatrimonioLocal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patrimonios",
    )

    numero_patrimonio = models.CharField(max_length=30)
    descricao = models.CharField(max_length=255)
    marca = models.CharField(max_length=100, blank=True, default="")
    modelo = models.CharField(max_length=100, blank=True, default="")
    numero_serie = models.CharField(max_length=100, blank=True, default="")
    cor = models.CharField(max_length=50, blank=True, default="")
    observacoes = models.TextField(blank=True, default="")

    valor_aquisicao = models.DecimalField(max_digits=15, decimal_places=2)
    data_aquisicao = models.DateField(null=True, blank=True)
    data_inicio_depreciacao = models.DateField(null=True, blank=True)
    valor_depreciado_acumulado = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    valor_liquido_contabil = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    nota_fiscal_numero = models.CharField(max_length=50, blank=True, default="")

    estado_conservacao = models.CharField(max_length=12, choices=ESTADO_CHOICES, default="bom")
    situacao = models.CharField(max_length=16, choices=SITUACAO_CHOICES, default="ativo")
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patrimonios_criados",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)  # soft delete

    class Meta:
        verbose_name = "Patrimônio"
        verbose_name_plural = "Patrimônios"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "numero_patrimonio"],
                name="uq_patrimonio_tenant_numero",
            ),
        ]
        indexes = [
            models.Index(fields=["situacao"]),
            models.Index(fields=["categoria"]),
            models.Index(fields=["local"]),
            models.Index(fields=["tenant", "secretaria"]),
        ]

    def __str__(self) -> str:
        return f"{self.numero_patrimonio} — {self.descricao}"

    def save(self, *args, **kwargs):
        if not self.numero_patrimonio:
            self.numero_patrimonio = self.gerar_numero_patrimonio(self.tenant_id)
        if self.data_aquisicao and not self.data_inicio_depreciacao:
            self.data_inicio_depreciacao = self.data_aquisicao
        if self.valor_liquido_contabil is None and self.valor_aquisicao is not None:
            self.valor_liquido_contabil = self.valor_aquisicao
        super().save(*args, **kwargs)

    @classmethod
    def gerar_numero_patrimonio(cls, tenant_id) -> str:
        ano = timezone.now().year
        n = cls.all_tenants.filter(
            tenant_id=tenant_id, numero_patrimonio__startswith=f"PATR-{ano}-"
        ).count() + 1
        return f"PATR-{ano}-{n:05d}"


# ---------------------------------------------------------------------------
# QR code (1:1 com Patrimonio)
# ---------------------------------------------------------------------------

class PatrimonioQrCode(TenantOwnedModel):
    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("inutilizado", "Inutilizado"),
    ]

    secretaria = models.ForeignKey(
        "organizacoes.Secretaria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patrimonio_qrcodes",
    )
    patrimonio = models.OneToOneField(
        Patrimonio,
        on_delete=models.CASCADE,
        related_name="qrcode",
    )
    codigo = models.CharField(max_length=10, unique=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="ativo")
    gerado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patrimonio_qrcodes_gerados",
    )
    gerado_em = models.DateTimeField(auto_now_add=True)
    impresso_em = models.DateTimeField(null=True, blank=True)
    qtd_impressoes = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "QR Code de Patrimônio"
        verbose_name_plural = "QR Codes de Patrimônio"

    def __str__(self) -> str:
        return self.codigo

    @classmethod
    def gerar_codigo_unico(cls, tamanho: int = 10) -> str:
        # Sem caracteres ambíguos (0/O, 1/I/L).
        alfabeto = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
        while True:
            codigo = "".join(random.choices(alfabeto, k=tamanho))
            if not cls.objects.filter(codigo=codigo).exists():
                return codigo


# ---------------------------------------------------------------------------
# Fotos do bem
# ---------------------------------------------------------------------------

class PatrimonioFoto(models.Model):
    patrimonio = models.ForeignKey(
        Patrimonio,
        on_delete=models.CASCADE,
        related_name="fotos",
    )
    caminho_arquivo = models.CharField(max_length=500)
    caminho_thumb = models.CharField(max_length=500, blank=True, default="")
    url_full = models.CharField(max_length=800, blank=True, default="")
    url_thumb = models.CharField(max_length=800, blank=True, default="")
    largura = models.PositiveSmallIntegerField(null=True, blank=True)
    altura = models.PositiveSmallIntegerField(null=True, blank=True)
    tamanho_bytes = models.PositiveIntegerField(null=True, blank=True)
    mime = models.CharField(max_length=50, default="image/jpeg")
    hash = models.CharField(max_length=64, blank=True, default="")
    principal = models.BooleanField(default=False)
    disk = models.CharField(max_length=30, default="public")
    legenda = models.CharField(max_length=255, blank=True, default="")
    ordem = models.PositiveIntegerField(default=0)
    enviado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patrimonio_fotos_enviadas",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Foto de Patrimônio"
        verbose_name_plural = "Fotos de Patrimônio"
        ordering = ["ordem", "id"]
        indexes = [
            models.Index(fields=["patrimonio", "ordem"]),
            models.Index(fields=["patrimonio", "principal"], name="pat_fotos_capa_idx"),
        ]

    def __str__(self) -> str:
        return f"foto#{self.pk} de {self.patrimonio_id}"


# ---------------------------------------------------------------------------
# Snapshot mensal de depreciação (RABM)
# ---------------------------------------------------------------------------

class PatrimonioDepreciacao(models.Model):
    patrimonio = models.ForeignKey(
        Patrimonio,
        on_delete=models.CASCADE,
        related_name="depreciacoes",
    )
    mes_referencia = models.DateField()  # sempre dia 01
    valor_depreciado_mes = models.DecimalField(max_digits=14, decimal_places=2)
    valor_acumulado_apos = models.DecimalField(max_digits=14, decimal_places=2)
    valor_liquido_apos = models.DecimalField(max_digits=14, decimal_places=2)
    metodo_aplicado = models.CharField(max_length=30)
    processado_em = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Depreciação de Patrimônio"
        verbose_name_plural = "Depreciações de Patrimônio"
        ordering = ["-mes_referencia"]
        constraints = [
            models.UniqueConstraint(
                fields=["patrimonio", "mes_referencia"],
                name="uq_pat_dep_patrimonio_mes",
            ),
        ]
        indexes = [models.Index(fields=["mes_referencia"])]

    def __str__(self) -> str:
        return f"{self.patrimonio_id} {self.mes_referencia:%Y-%m}"


# ---------------------------------------------------------------------------
# Audit log de cadastros via IA Vision
# ---------------------------------------------------------------------------

class PatrimonioCadastroIa(TenantOwnedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patrimonio_cadastros_ia",
    )
    imagem_hash = models.CharField(max_length=64, db_index=True)
    modelo_usado = models.CharField(max_length=60)
    resposta_bruta = models.JSONField()
    multiplos_bens = models.BooleanField(default=False)
    tokens_input = models.PositiveSmallIntegerField(null=True, blank=True)
    tokens_output = models.PositiveSmallIntegerField(null=True, blank=True)
    custo_estimado_brl = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    patrimonio = models.ForeignKey(
        Patrimonio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cadastros_ia",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cadastro via IA"
        verbose_name_plural = "Cadastros via IA"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "imagem_hash"],
                name="uq_pat_ia_tenant_hash",
            ),
        ]

    def __str__(self) -> str:
        return f"IA #{self.pk} hash={self.imagem_hash[:8]}"
