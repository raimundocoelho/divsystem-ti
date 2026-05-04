from django.contrib import admin

from apps.mikrotik.models import (
    Comando,
    Device,
    DeviceObservation,
    Equipamento,
    RogueAlert,
)


@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "modelo", "wg_ip", "status", "ativo", "tenant", "updated_at")
    list_filter = ("status", "modelo", "ativo", "tenant")
    search_fields = ("nome", "slug", "mac_address", "serial_number", "wg_ip")
    readonly_fields = (
        "slug",
        "wg_pubkey_device",
        "wg_privkey_device",
        "wg_handshake_at",
        "last_seen_at",
        "last_error",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (None, {"fields": ("tenant", "nome", "slug", "descricao", "modelo", "ativo", "status")}),
        ("Hardware", {"fields": ("serial_number", "mac_address", "routeros_version")}),
        ("Localização", {"fields": ("secretaria", "setor", "endereco")}),
        ("WireGuard", {
            "fields": (
                "wg_ip",
                "wg_endpoint_host",
                "wg_endpoint_port",
                "wg_pubkey_device",
                "wg_privkey_device",
                "wg_handshake_at",
            ),
        }),
        ("API REST", {"fields": ("api_user", "api_password", "api_port", "api_use_https")}),
        ("Auditoria", {"fields": ("criado_por", "last_seen_at", "last_error", "created_at", "updated_at")}),
    )


@admin.register(Comando)
class ComandoAdmin(admin.ModelAdmin):
    list_display = ("created_at", "equipamento", "tipo", "path", "status", "duration_ms")
    list_filter = ("status", "tipo", "tenant")
    search_fields = ("path", "equipamento__nome")
    readonly_fields = (
        "tenant",
        "equipamento",
        "tipo",
        "path",
        "payload",
        "status",
        "response_status",
        "response_body",
        "erro",
        "duration_ms",
        "executado_por",
        "created_at",
        "completed_at",
    )
    date_hierarchy = "created_at"


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "nome",
        "tipo",
        "mac_address",
        "ip_address",
        "equipamento",
        "status",
        "last_seen_at",
    )
    list_filter = ("status", "tipo", "equipamento", "tenant")
    search_fields = ("nome", "mac_address", "ip_address", "hostname", "responsavel")
    readonly_fields = ("last_seen_at", "last_seen_interface", "synced_at", "sync_error", "created_at", "updated_at")


@admin.register(DeviceObservation)
class DeviceObservationAdmin(admin.ModelAdmin):
    list_display = ("seen_at", "equipamento", "mac_address", "ip_address", "interface", "source")
    list_filter = ("source", "equipamento", "tenant")
    search_fields = ("mac_address", "ip_address", "hostname")
    date_hierarchy = "seen_at"


@admin.register(RogueAlert)
class RogueAlertAdmin(admin.ModelAdmin):
    list_display = ("ultima_vez", "equipamento", "mac_address", "primeiro_ip", "primeiro_hostname", "status", "contagem")
    list_filter = ("status", "equipamento", "tenant")
    search_fields = ("mac_address", "primeiro_ip", "primeiro_hostname")
    readonly_fields = ("primeiro_visto", "ultima_vez", "contagem")
