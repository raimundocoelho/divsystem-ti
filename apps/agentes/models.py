"""Modelos do módulo Agentes — AgentToken, AgentHeartbeat, RemoteCommand.

`AgentToken.online_status` calcula o estado em runtime, igual ao Laravel:
- v >= 5.2.0 (`AGENT_VERSION_PING_LEVE`): thresholds curtos sobre `last_ping_at`.
- v <  5.2.0: thresholds longos sobre `last_seen_at`.
"""
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TenantOwnedModel


def _generate_agent_token() -> str:
    return secrets.token_hex(32)


class AgentToken(TenantOwnedModel):
    """Token Bearer único por agente — mapeia 1:1 com uma máquina."""

    name = models.CharField(max_length=255)
    token = models.CharField(max_length=64, unique=True, db_index=True)
    machine_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    hostname = models.CharField(max_length=255, blank=True, default="")

    secretaria = models.ForeignKey(
        "organizacoes.Secretaria",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_tokens",
    )
    setor = models.ForeignKey(
        "organizacoes.Setor",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agent_tokens",
    )

    agent_version = models.CharField(max_length=20, blank=True, default="")
    agent_updated_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    active = models.BooleanField(default=True)
    is_canary = models.BooleanField(default=False, help_text="Recebe builds beta antes do rollout geral.")

    last_seen_at = models.DateTimeField(null=True, blank=True)
    last_ping_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Agente"
        verbose_name_plural = "Agentes"
        ordering = ["-last_seen_at", "name"]
        indexes = [
            models.Index(fields=["tenant", "active"]),
            models.Index(fields=["machine_id"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.hostname or self.machine_id or self.id})"

    @classmethod
    def generate_token(cls) -> str:
        return _generate_agent_token()

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = _generate_agent_token()
        super().save(*args, **kwargs)

    # --- Computed status ----------------------------------------------------

    def _has_light_ping(self) -> bool:
        if not self.agent_version:
            return False
        try:
            return _version_tuple(self.agent_version) >= _version_tuple(settings.AGENT_VERSION_PING_LEVE)
        except ValueError:
            return False

    @property
    def online_status(self) -> str:
        if not self.active:
            return "inativo"
        now = timezone.now()
        ref = self.last_ping_at if self._has_light_ping() else self.last_seen_at
        if not ref:
            return "aguardando"
        elapsed = (now - ref).total_seconds()
        if self._has_light_ping():
            warn, off = 180, 600
        else:
            warn, off = 2100, 4200
        if elapsed <= warn:
            return "online"
        if elapsed <= off:
            return "warning"
        return "offline"

    def online_status_color(self) -> str:
        return {
            "online": "green",
            "warning": "yellow",
            "offline": "red",
            "inativo": "zinc",
            "aguardando": "zinc",
        }[self.online_status]

    def online_status_label(self) -> str:
        return {
            "online": "Online",
            "warning": "Atrasado",
            "offline": "Offline",
            "inativo": "Inativo",
            "aguardando": "Aguardando primeiro contato",
        }[self.online_status]


def _version_tuple(v: str):
    return tuple(int(p) for p in v.strip().split(".") if p.isdigit())


class AgentHeartbeat(models.Model):
    """Snapshot de inventário enviado pelo agente.

    Não usa `TenantOwnedModel` direto: o tenant é inferido via `agent_token`. Mas
    mantemos `tenant_id` denormalizado para joins rápidos e auditoria cross-tenant.
    """

    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.CASCADE,
        related_name="agent_heartbeats",
        null=True,
        blank=True,
        db_index=True,
    )
    agent_token = models.ForeignKey(
        AgentToken,
        on_delete=models.CASCADE,
        related_name="heartbeats",
    )
    machine_id = models.CharField(max_length=255, db_index=True)
    agent_version = models.CharField(max_length=20, blank=True, default="")

    hardware = models.JSONField(null=True, blank=True)
    network = models.JSONField(null=True, blank=True)
    system_info = models.JSONField(null=True, blank=True)
    software = models.JSONField(null=True, blank=True)
    peripherals = models.JSONField(null=True, blank=True)
    alerts = models.JSONField(null=True, blank=True)

    collected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Heartbeat"
        verbose_name_plural = "Heartbeats"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["machine_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"hb#{self.pk} {self.machine_id} @ {self.created_at}"


class RemoteCommand(models.Model):
    """Comando remoto despachado para um agente — fila de tarefas via polling."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        SENT = "sent", "Enviado"
        RUNNING = "running", "Executando"
        SUCCESS = "success", "Sucesso"
        FAILED = "failed", "Falhou"
        TIMEOUT = "timeout", "Tempo esgotado"

    COMMANDS = {
        "screenshot_now":   {"label": "Captura de Tela", "payload": [], "critical": False},
        "usb_block":        {"label": "Bloquear USB", "payload": ["hardware_id"], "critical": False},
        "usb_block_all":    {"label": "Bloquear todos USB", "payload": [], "critical": True},
        "usb_unblock":      {"label": "Desbloquear USB", "payload": ["hardware_id"], "critical": False},
        "usb_eject":        {"label": "Ejetar USB", "payload": ["drive_letter"], "critical": False},
        "send_message":     {"label": "Enviar mensagem", "payload": ["title", "message", "type"], "critical": False},
        "shutdown":         {"label": "Desligar", "payload": ["delay_seconds"], "critical": True},
        "restart":          {"label": "Reiniciar", "payload": ["delay_seconds"], "critical": True},
        "lock_screen":      {"label": "Bloquear tela", "payload": [], "critical": False},
        "run_command":      {"label": "Executar comando", "payload": ["command", "args"], "critical": True},
        "open_url":         {"label": "Abrir URL", "payload": ["url"], "critical": False},
        "kill_process":     {"label": "Encerrar processo", "payload": ["process_name"], "critical": True},
        "update_agent":     {"label": "Atualizar agente", "payload": [], "critical": False},
        "apply_policies":   {"label": "Aplicar políticas", "payload": [], "critical": False},
        "change_ip":        {"label": "Alterar IP", "payload": ["ip", "mask", "gateway", "dns1", "dns2", "dhcp"], "critical": True},
        "rename_pc":        {"label": "Renomear PC", "payload": ["new_name", "restart"], "critical": True},
        "set_wallpaper":    {"label": "Papel de parede", "payload": ["image_url"], "critical": False},
        "deploy_agent":     {"label": "Instalar agente remoto", "payload": ["target_ip", "username", "password", "enroll_code", "server_url"], "critical": True},
        "uninstall_agent":  {"label": "Desinstalar agente", "payload": [], "critical": True},
    }

    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.CASCADE,
        related_name="remote_commands",
        null=True,
        blank=True,
        db_index=True,
    )
    agent_token = models.ForeignKey(
        AgentToken,
        on_delete=models.CASCADE,
        related_name="remote_commands",
    )
    command = models.CharField(max_length=64)
    payload = models.JSONField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    output = models.TextField(blank=True, default="")
    error = models.TextField(blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="remote_commands_created",
    )

    sent_at = models.DateTimeField(null=True, blank=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Comando remoto"
        verbose_name_plural = "Comandos remotos"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["agent_token", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.command} → {self.agent_token_id} [{self.status}]"

    @property
    def is_critical(self) -> bool:
        return bool(self.COMMANDS.get(self.command, {}).get("critical"))

    @property
    def command_label(self) -> str:
        return self.COMMANDS.get(self.command, {}).get("label", self.command)

    def status_color(self) -> str:
        return {
            "pending": "yellow",
            "sent": "blue",
            "running": "cyan",
            "success": "green",
            "failed": "red",
            "timeout": "orange",
        }.get(self.status, "zinc")

    @classmethod
    def mark_timed_out(cls, minutes: int = 5) -> int:
        cutoff = timezone.now() - timezone.timedelta(minutes=minutes)
        return cls.objects.filter(
            status__in=[cls.Status.PENDING, cls.Status.SENT],
            created_at__lt=cutoff,
        ).update(status=cls.Status.TIMEOUT, completed_at=timezone.now())
