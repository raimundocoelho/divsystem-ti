from django.contrib import admin

from .models import (
    AgentHeartbeat,
    AgentToken,
    BlockedSite,
    RemoteCommand,
    SitePolicy,
    SiteRule,
    WorkstationPolicy,
)


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


class SiteRuleInline(admin.TabularInline):
    model = SiteRule
    extra = 0
    fields = ("domain", "action", "category")


@admin.register(SitePolicy)
class SitePolicyAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "is_global", "active", "created_by", "created_at")
    list_filter = ("active", "is_global", "tenant")
    search_fields = ("name", "description")
    inlines = [SiteRuleInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(SiteRule)
class SiteRuleAdmin(admin.ModelAdmin):
    list_display = ("domain", "action", "category", "site_policy", "created_at")
    list_filter = ("action", "category")
    search_fields = ("domain",)


@admin.register(WorkstationPolicy)
class WorkstationPolicyAdmin(admin.ModelAdmin):
    list_display = ("site_policy", "agent_token", "applied_at", "updated_at")
    search_fields = ("site_policy__name", "agent_token__hostname")
    readonly_fields = ("applied_at", "created_at", "updated_at")


@admin.register(BlockedSite)
class BlockedSiteAdmin(admin.ModelAdmin):
    list_display = ("domain", "tenant", "active", "reason", "created_by", "created_at")
    list_filter = ("active", "tenant")
    search_fields = ("domain", "reason")
