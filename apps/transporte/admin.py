from django.contrib import admin

from .models import (
    CidadeDestino,
    HorarioTransporte,
    LocalAtendimento,
    LocalEmbarque,
    Motorista,
    Paciente,
    PassageiroViagem,
    ProtocoloExame,
    ViagemTransporte,
)


@admin.register(CidadeDestino)
class CidadeDestinoAdmin(admin.ModelAdmin):
    list_display = ("nome", "uf", "ativo", "tenant")
    list_filter = ("uf", "ativo", "tenant")
    search_fields = ("nome",)


@admin.register(LocalAtendimento)
class LocalAtendimentoAdmin(admin.ModelAdmin):
    list_display = ("nome", "cidade_destino", "telefone", "ativo", "tenant")
    list_filter = ("ativo", "cidade_destino", "tenant")
    search_fields = ("nome", "endereco")


@admin.register(LocalEmbarque)
class LocalEmbarqueAdmin(admin.ModelAdmin):
    list_display = ("nome", "hora", "ativo", "tenant")
    list_filter = ("ativo", "tenant")
    search_fields = ("nome", "endereco")


@admin.register(HorarioTransporte)
class HorarioTransporteAdmin(admin.ModelAdmin):
    list_display = ("hora", "descricao", "ordem", "ativo", "tenant")
    list_filter = ("ativo", "tenant")


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "cns", "data_nascimento", "unidade", "ativo", "tenant")
    list_filter = ("ativo", "sexo", "unidade", "tenant")
    search_fields = ("nome", "cpf", "cns", "cds_individual")


@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display = ("nome", "cpf", "cnh", "cnh_categoria", "cnh_validade", "ativo", "tenant")
    list_filter = ("cnh_categoria", "ativo", "tenant")
    search_fields = ("nome", "cpf", "cnh")
    readonly_fields = ("access_token", "last_seen_at")


class PassageiroViagemInline(admin.TabularInline):
    model = PassageiroViagem
    extra = 0
    fields = ("paciente", "acompanhante", "local_atendimento", "local_embarque", "finalidade", "presente")


@admin.register(ViagemTransporte)
class ViagemTransporteAdmin(admin.ModelAdmin):
    list_display = ("id", "data", "hora_saida", "cidade_destino", "veiculo", "motorista", "status", "tenant")
    list_filter = ("status", "tipo", "cidade_destino", "tenant")
    search_fields = ("observacoes",)
    inlines = [PassageiroViagemInline]


@admin.register(PassageiroViagem)
class PassageiroViagemAdmin(admin.ModelAdmin):
    list_display = ("id", "viagem", "paciente", "local_atendimento", "finalidade", "presente", "embarcou_em")
    list_filter = ("presente",)
    search_fields = ("paciente__nome", "finalidade")


@admin.register(ProtocoloExame)
class ProtocoloExameAdmin(admin.ModelAdmin):
    list_display = ("id", "paciente", "tipo", "descricao", "status", "previsao_retirada", "tenant")
    list_filter = ("status", "tipo", "tenant")
    search_fields = ("descricao", "numero_protocolo")
