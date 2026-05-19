from django.contrib import admin

from .models import (
    Patrimonio,
    PatrimonioCadastroIa,
    PatrimonioCategoria,
    PatrimonioDepreciacao,
    PatrimonioFoto,
    PatrimonioLocal,
    PatrimonioQrCode,
)


@admin.register(PatrimonioCategoria)
class PatrimonioCategoriaAdmin(admin.ModelAdmin):
    list_display = ("codigo_mcasp", "nome", "metodo_depreciacao", "vida_util_anos", "deprecia", "ativo", "tenant")
    list_filter = ("metodo_depreciacao", "deprecia", "ativo", "tenant")
    search_fields = ("nome", "codigo_mcasp", "nome_conta_pcasp")


@admin.register(PatrimonioLocal)
class PatrimonioLocalAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "parent", "secretaria", "setor", "tenant")
    list_filter = ("tipo", "tenant", "secretaria")
    search_fields = ("nome", "endereco")


class PatrimonioFotoInline(admin.TabularInline):
    model = PatrimonioFoto
    extra = 0
    fields = ("ordem", "principal", "legenda", "url_thumb")
    readonly_fields = ("url_thumb",)


@admin.register(Patrimonio)
class PatrimonioAdmin(admin.ModelAdmin):
    list_display = ("numero_patrimonio", "descricao", "categoria", "local", "situacao", "valor_aquisicao", "tenant")
    list_filter = ("situacao", "estado_conservacao", "categoria", "tenant")
    search_fields = ("numero_patrimonio", "descricao", "marca", "modelo", "numero_serie")
    inlines = [PatrimonioFotoInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(PatrimonioQrCode)
class PatrimonioQrCodeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "patrimonio", "status", "qtd_impressoes", "impresso_em", "tenant")
    list_filter = ("status", "tenant")
    search_fields = ("codigo",)


@admin.register(PatrimonioFoto)
class PatrimonioFotoAdmin(admin.ModelAdmin):
    list_display = ("id", "patrimonio", "principal", "ordem", "mime", "tamanho_bytes")
    list_filter = ("principal", "mime")
    search_fields = ("patrimonio__numero_patrimonio", "patrimonio__descricao")


@admin.register(PatrimonioDepreciacao)
class PatrimonioDepreciacaoAdmin(admin.ModelAdmin):
    list_display = ("patrimonio", "mes_referencia", "valor_depreciado_mes", "valor_liquido_apos", "metodo_aplicado")
    list_filter = ("metodo_aplicado",)
    search_fields = ("patrimonio__numero_patrimonio",)


@admin.register(PatrimonioCadastroIa)
class PatrimonioCadastroIaAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "modelo_usado", "multiplos_bens", "tokens_input", "tokens_output", "custo_estimado_brl", "tenant")
    list_filter = ("modelo_usado", "multiplos_bens", "tenant")
    search_fields = ("imagem_hash",)
    readonly_fields = ("imagem_hash", "resposta_bruta")
