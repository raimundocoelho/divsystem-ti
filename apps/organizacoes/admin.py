from django.contrib import admin

from .models import Secretaria, Setor


@admin.register(Secretaria)
class SecretariaAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo", "tenant", "ativo", "responsavel")
    list_filter = ("ativo", "tenant")
    search_fields = ("nome", "codigo", "responsavel")
    readonly_fields = ("slug", "created_at", "updated_at")


@admin.register(Setor)
class SetorAdmin(admin.ModelAdmin):
    list_display = ("nome", "secretaria", "tenant", "ativo", "localizacao")
    list_filter = ("ativo", "tenant", "secretaria")
    search_fields = ("nome", "localizacao", "responsavel")
