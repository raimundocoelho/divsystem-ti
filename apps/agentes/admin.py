from django.contrib import admin

from .models import AgentHeartbeat, AgentToken, RemoteCommand


@admin.register(AgentToken)
class AgentTokenAdmin(admin.ModelAdmin):
    list_display = ("name", "hostname", "tenant", "agent_version", "active", "last_seen_at")
    list_filter = ("active", "is_canary", "tenant")
    search_fields = ("name", "hostname", "machine_id", "token")
    readonly_fields = ("token", "machine_id", "last_seen_at", "last_ping_at", "created_at", "updated_at")


@admin.register(AgentHeartbeat)
class AgentHeartbeatAdmin(admin.ModelAdmin):
    list_display = ("id", "agent_token", "machine_id", "agent_version", "collected_at", "created_at")
    list_filter = ("tenant",)
    search_fields = ("machine_id",)
    readonly_fields = tuple(f.name for f in AgentHeartbeat._meta.fields)


@admin.register(RemoteCommand)
class RemoteCommandAdmin(admin.ModelAdmin):
    list_display = ("id", "command", "agent_token", "status", "created_at", "completed_at")
    list_filter = ("status", "command", "tenant")
    search_fields = ("command", "output", "error")
    readonly_fields = ("created_at", "updated_at", "sent_at", "executed_at", "completed_at")
