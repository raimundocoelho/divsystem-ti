"""Modelos do módulo Mikrotik.

Equipamento → roteador Mikrotik provisionado via WireGuard, atrelado a um tenant
(prefeitura) e opcionalmente a uma Secretaria/Setor.

Comando → registro auditável de cada chamada feita ao equipamento via REST API.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import TenantOwnedModel


class Equipamento(TenantOwnedModel):
    MODELO_CHOICES = [
        ("hex_e50ug", "hEX E50UG"),
        ("hex_refresh", "hEX Refresh (RB750Gr3)"),
        ("hap_ax2", "hAP ax²"),
        ("hap_ax3", "hAP ax³"),
        ("ccr2004", "CCR2004"),
        ("crs", "CRS (switch)"),
        ("outro", "Outro Mikrotik"),
    ]

    STATUS_CHOICES = [
        ("provisionando", "Provisionando"),
        ("aguardando_bootstrap", "Aguardando bootstrap"),
        ("online", "Online"),
        ("offline", "Offline"),
        ("erro", "Erro"),
        ("desativado", "Desativado"),
    ]

    nome = models.CharField(max_length=120)
    slug = models.SlugField(max_length=160, blank=True)
    descricao = models.CharField(max_length=255, blank=True, default="")

    modelo = models.CharField(max_length=32, choices=MODELO_CHOICES, default="hex_e50ug")
    serial_number = models.CharField(max_length=64, blank=True, default="")
    mac_address = models.CharField(max_length=17, blank=True, default="")
    routeros_version = models.CharField(max_length=32, blank=True, default="")

    secretaria = models.ForeignKey(
        "organizacoes.Secretaria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipamentos_mikrotik",
    )
    setor = models.ForeignKey(
        "organizacoes.Setor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipamentos_mikrotik",
    )
    endereco = models.CharField(max_length=255, blank=True, default="")

    wg_pubkey_device = models.CharField(max_length=64, blank=True, default="")
    wg_privkey_device = models.CharField(max_length=64, blank=True, default="")
    wg_ip = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    wg_handshake_at = models.DateTimeField(null=True, blank=True)
    wg_endpoint_host = models.CharField(max_length=255, blank=True, default="")
    wg_endpoint_port = models.PositiveIntegerField(default=51820)

    api_user = models.CharField(max_length=64, default="divsystem")
    api_password = models.CharField(max_length=128, blank=True, default="")
    api_port = models.PositiveIntegerField(default=443)
    api_use_https = models.BooleanField(default=True)

    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default="provisionando")
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True, default="")

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mikrotik_equipamentos_criados",
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Equipamento Mikrotik"
        verbose_name_plural = "Equipamentos Mikrotik"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(fields=["tenant", "slug"], name="uq_mikrotik_tenant_slug"),
            models.UniqueConstraint(
                fields=["wg_ip"],
                name="uq_mikrotik_wg_ip",
                condition=~models.Q(wg_ip=None),
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["tenant", "ativo"]),
        ]

    def __str__(self) -> str:
        return f"{self.nome} ({self.get_modelo_display()})"

    def save(self, *args, **kwargs):
        if not self.slug or self._state.adding:
            base = slugify(self.nome) or "equipamento"
            slug = base
            n = 2
            qs = Equipamento.all_tenants.filter(tenant_id=self.tenant_id, slug=slug)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            while qs.exists():
                slug = f"{base}-{n}"
                n += 1
                qs = Equipamento.all_tenants.filter(tenant_id=self.tenant_id, slug=slug)
                if self.pk:
                    qs = qs.exclude(pk=self.pk)
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def api_base_url(self) -> str:
        scheme = "https" if self.api_use_https else "http"
        return f"{scheme}://{self.wg_ip}:{self.api_port}/rest"


class Comando(TenantOwnedModel):
    TIPO_CHOICES = [
        ("rest_get", "REST GET"),
        ("rest_post", "REST POST"),
        ("rest_put", "REST PUT"),
        ("rest_patch", "REST PATCH"),
        ("rest_delete", "REST DELETE"),
        ("execute", "Comando RouterOS (execute)"),
    ]

    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("executando", "Executando"),
        ("sucesso", "Sucesso"),
        ("erro", "Erro"),
    ]

    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.CASCADE,
        related_name="comandos",
    )
    tipo = models.CharField(max_length=16, choices=TIPO_CHOICES)
    path = models.CharField(max_length=512, help_text="Ex.: /system/identity ou /ip/firewall/filter")
    payload = models.JSONField(blank=True, null=True)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pendente")
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.JSONField(blank=True, null=True)
    erro = models.TextField(blank=True, default="")
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    executado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mikrotik_comandos",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Comando Mikrotik"
        verbose_name_plural = "Comandos Mikrotik"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "equipamento", "-created_at"]),
            models.Index(fields=["tenant", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.tipo} {self.path} → {self.equipamento.nome} [{self.status}]"


def _normalize_mac(value: str) -> str:
    """Normaliza MAC pra UPPER:CASE com `:` separador."""
    if not value:
        return ""
    cleaned = "".join(c for c in value if c.isalnum()).upper()
    if len(cleaned) != 12:
        return value.upper()
    return ":".join(cleaned[i:i + 2] for i in range(0, 12, 2))


class Device(TenantOwnedModel):
    """Dispositivo autorizado a usar a rede gerenciada por um Equipamento Mikrotik."""

    TIPO_CHOICES = [
        ("computador", "Computador"),
        ("notebook", "Notebook"),
        ("impressora", "Impressora"),
        ("celular", "Celular"),
        ("tablet", "Tablet"),
        ("tv", "Smart TV"),
        ("camera", "Câmera IP"),
        ("ap", "Access Point"),
        ("voip", "VoIP / Telefone IP"),
        ("servidor", "Servidor"),
        ("iot", "IoT / Outro"),
    ]

    STATUS_CHOICES = [
        ("ativo", "Ativo"),
        ("bloqueado", "Bloqueado"),
        ("desativado", "Desativado"),
    ]

    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.CASCADE,
        related_name="devices",
    )
    nome = models.CharField(max_length=120)
    descricao = models.CharField(max_length=255, blank=True, default="")
    tipo = models.CharField(max_length=16, choices=TIPO_CHOICES, default="computador")

    mac_address = models.CharField(max_length=17)
    ip_address = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    hostname = models.CharField(max_length=120, blank=True, default="")

    secretaria = models.ForeignKey(
        "organizacoes.Secretaria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices",
    )
    setor = models.ForeignKey(
        "organizacoes.Setor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devices",
    )
    responsavel = models.CharField(max_length=120, blank=True, default="")

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="ativo")
    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_seen_interface = models.CharField(max_length=32, blank=True, default="")

    # Estado da sincronização com o router
    synced_at = models.DateTimeField(null=True, blank=True)
    sync_error = models.TextField(blank=True, default="")

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mikrotik_devices_criados",
    )
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dispositivo de rede"
        verbose_name_plural = "Dispositivos de rede"
        ordering = ["nome"]
        constraints = [
            models.UniqueConstraint(
                fields=["equipamento", "mac_address"],
                name="uq_device_eq_mac",
            ),
            models.UniqueConstraint(
                fields=["equipamento", "ip_address"],
                name="uq_device_eq_ip",
                condition=~models.Q(ip_address=None),
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "equipamento", "status"]),
            models.Index(fields=["tenant", "mac_address"]),
        ]

    def __str__(self) -> str:
        return f"{self.nome} [{self.mac_address}]"

    def save(self, *args, **kwargs):
        self.mac_address = _normalize_mac(self.mac_address)
        super().save(*args, **kwargs)


class DeviceObservation(TenantOwnedModel):
    """Cada vez que pull_observations roda, registra o que foi visto.

    Usado pra histórico de presença + detecção de rogues. Não tem FK pra Device
    porque pode ser um MAC desconhecido (rogue).
    """

    SOURCE_CHOICES = [
        ("dhcp", "DHCP lease"),
        ("arp", "ARP table"),
        ("bridge", "Bridge host"),
    ]

    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.CASCADE,
        related_name="device_observations",
    )
    mac_address = models.CharField(max_length=17)
    ip_address = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    hostname = models.CharField(max_length=120, blank=True, default="")
    interface = models.CharField(max_length=32, blank=True, default="")
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES)
    seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Observação de dispositivo"
        verbose_name_plural = "Observações de dispositivos"
        ordering = ["-seen_at"]
        indexes = [
            models.Index(fields=["tenant", "equipamento", "mac_address", "-seen_at"]),
            models.Index(fields=["tenant", "-seen_at"]),
        ]

    def save(self, *args, **kwargs):
        self.mac_address = _normalize_mac(self.mac_address)
        super().save(*args, **kwargs)


class RogueAlert(TenantOwnedModel):
    """MAC visto na rede mas sem Device cadastrado — alerta pro operador."""

    STATUS_CHOICES = [
        ("novo", "Novo"),
        ("aceito", "Aceito (cadastrado como Device)"),
        ("bloqueado", "Bloqueado"),
        ("ignorado", "Ignorado"),
    ]

    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.CASCADE,
        related_name="rogue_alerts",
    )
    mac_address = models.CharField(max_length=17)
    primeiro_ip = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True)
    primeiro_hostname = models.CharField(max_length=120, blank=True, default="")
    primeiro_interface = models.CharField(max_length=32, blank=True, default="")

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="novo")
    contagem = models.PositiveIntegerField(default=1)
    primeiro_visto = models.DateTimeField(auto_now_add=True)
    ultima_vez = models.DateTimeField(auto_now=True)

    resolvido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mikrotik_rogues_resolvidos",
    )
    resolvido_em = models.DateTimeField(null=True, blank=True)
    nota = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "Alerta de dispositivo desconhecido"
        verbose_name_plural = "Alertas de dispositivos desconhecidos"
        ordering = ["-ultima_vez"]
        constraints = [
            models.UniqueConstraint(
                fields=["equipamento", "mac_address"],
                name="uq_rogue_eq_mac",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "equipamento", "status"]),
        ]

    def save(self, *args, **kwargs):
        self.mac_address = _normalize_mac(self.mac_address)
        super().save(*args, **kwargs)


# === Políticas de filtro web (DNS sinkhole + firewall TLS-SNI por src-mac) ====
class Politica(TenantOwnedModel):
    """Política de bloqueio de sites para um Equipamento.

    Uma política tem N domínios (RegraDominio) e M dispositivos alvo (PoliticaAlvo).
    Ao "aplicar" no router:
      - Cada domínio vira uma entrada em /ip/dns/static apontando pra 0.0.0.0
        (com regexp se incluir_subdominios=True). DNS sinkhole afeta todos os
        devices que usam o resolver da hEX — limitação conhecida.
      - Cada par (alvo, dominio) vira uma regra em /ip/firewall/filter
        chain=forward, src-mac-address=<alvo.mac>, tls-host=*<dominio>*,
        action=drop, dst-port=443/tcp. Pega quem tenta burlar o DNS via DoH/DoT.
    """

    equipamento = models.ForeignKey(
        Equipamento,
        on_delete=models.CASCADE,
        related_name="politicas",
    )
    nome = models.CharField(max_length=120)
    descricao = models.CharField(max_length=255, blank=True, default="")
    ativo = models.BooleanField(default=True)
    is_global = models.BooleanField(default=False, help_text="Aplica em todos os clientes do hEX (DNS sinkhole apenas, sem firewall por src-mac).")
    aplicada_em = models.DateTimeField(null=True, blank=True)
    aplicada_erro = models.TextField(blank=True, default="")

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mikrotik_politicas_criadas",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Política de filtro"
        verbose_name_plural = "Políticas de filtro"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["equipamento", "nome"],
                name="uq_politica_eq_nome",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant", "equipamento", "ativo"]),
        ]

    def __str__(self) -> str:
        return f"{self.nome} [{self.equipamento.slug}]"

    # === métodos de categoria (toggle bulk-add/remove de domínios curados) ===
    def categorias_ativas(self) -> list[str]:
        return sorted(set(
            self.regras.exclude(categoria="").values_list("categoria", flat=True)
        ))

    def add_categoria(self, slug: str) -> int:
        from apps.mikrotik.services.categorias import dominios_da_categoria
        from django.db import IntegrityError
        n = 0
        for dom in dominios_da_categoria(slug):
            try:
                RegraDominio.objects.create(
                    politica=self,
                    dominio=dom,
                    categoria=slug,
                    incluir_subdominios=True,
                )
                n += 1
            except IntegrityError:
                pass
        return n

    def remove_categoria(self, slug: str) -> int:
        n, _ = self.regras.filter(categoria=slug).delete()
        return n


class RegraDominio(models.Model):
    """Domínio bloqueado por uma Política."""

    politica = models.ForeignKey(
        Politica,
        on_delete=models.CASCADE,
        related_name="regras",
    )
    dominio = models.CharField(max_length=255)
    incluir_subdominios = models.BooleanField(
        default=True,
        help_text="Se ligado, bloqueia também *.<dominio> (ex.: m.facebook.com).",
    )
    categoria = models.CharField(max_length=64, blank=True, default="", help_text="Slug da categoria curada (redes_sociais, streaming, ...) ou vazio se domínio individual.")
    comentario = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Regra de domínio"
        verbose_name_plural = "Regras de domínio"
        ordering = ["dominio"]
        constraints = [
            models.UniqueConstraint(
                fields=["politica", "dominio"],
                name="uq_regradominio_politica_dominio",
            ),
        ]

    def __str__(self) -> str:
        return self.dominio

    def save(self, *args, **kwargs):
        # Normaliza domínio: lower, sem http(s)://, sem trailing slash
        d = (self.dominio or "").strip().lower()
        for prefix in ("http://", "https://"):
            if d.startswith(prefix):
                d = d[len(prefix):]
        d = d.rstrip("/")
        # Remove "www." porque incluir_subdominios já cobre
        if d.startswith("www."):
            d = d[4:]
        self.dominio = d
        super().save(*args, **kwargs)


class PoliticaAlvo(models.Model):
    """Device alvo de uma Política."""

    politica = models.ForeignKey(
        Politica,
        on_delete=models.CASCADE,
        related_name="alvos",
    )
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="politicas_aplicadas",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Alvo de política"
        verbose_name_plural = "Alvos de política"
        constraints = [
            models.UniqueConstraint(
                fields=["politica", "device"],
                name="uq_politicaalvo_politica_device",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.politica.nome} → {self.device.nome}"
