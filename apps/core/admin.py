from django.contrib import admin

from .models import Tenant


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "city", "state", "active", "created_at")
    list_filter = ("active", "state")
    search_fields = ("name", "code", "cnpj", "city", "external_code")
    readonly_fields = ("code", "master_key", "slug", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("name", "active", "code", "slug", "external_code")}),
        ("Identificação", {"fields": ("cnpj", "contact_name", "email", "phone")}),
        ("Endereço", {"fields": ("address", "city", "state")}),
        ("Marca", {"fields": ("logo_url",)}),
        ("Segurança (agentes)", {"fields": ("master_key",)}),
        ("Auditoria", {"fields": ("created_at", "updated_at")}),
    )
