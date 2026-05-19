from django.contrib import admin

from .models import DiarioBordo, ManutencaoTipo, RegistroHoras, Veiculo


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ("placa", "nome", "modelo", "secretaria", "capacidade_passageiros", "tenant")
    list_filter = ("secretaria", "tenant")
    search_fields = ("placa", "nome", "modelo", "renavam", "chassi")


@admin.register(ManutencaoTipo)
class ManutencaoTipoAdmin(admin.ModelAdmin):
    list_display = ("nome", "intervalo_dias", "duracao_estimada_minutos", "ativo", "tenant")
    list_filter = ("ativo", "tenant")
    search_fields = ("nome", "descricao")


@admin.register(DiarioBordo)
class DiarioBordoAdmin(admin.ModelAdmin):
    list_display = ("id", "veiculo", "motorista", "condutor", "saida_em", "retorno_em", "destino", "tenant")
    list_filter = ("veiculo", "tenant")
    search_fields = ("destino", "finalidade")
    readonly_fields = ("created_at", "updated_at")


@admin.register(RegistroHoras)
class RegistroHorasAdmin(admin.ModelAdmin):
    list_display = ("data", "user", "total_horas", "tipo_atividade", "competencia")
    list_filter = ("tipo_atividade", "competencia")
    search_fields = ("observacao",)
