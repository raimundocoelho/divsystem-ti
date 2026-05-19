from django.urls import path

from . import views

app_name = "transporte"

urlpatterns = [
    # Cidades-Destino
    path("cidades/", views.cidade_list, name="cidade_list"),
    path("cidades/salvar/", views.cidade_save, name="cidade_create"),
    path("cidades/<int:pk>/salvar/", views.cidade_save, name="cidade_save"),
    path("cidades/<int:pk>/excluir/", views.cidade_delete, name="cidade_delete"),
    path("cidades/<int:pk>/toggle/", views.cidade_toggle, name="cidade_toggle"),

    # Locais de atendimento
    path("locais-atendimento/", views.local_atendimento_list, name="local_atendimento_list"),
    path("locais-atendimento/salvar/", views.local_atendimento_save, name="local_atendimento_create"),
    path("locais-atendimento/<int:pk>/salvar/", views.local_atendimento_save, name="local_atendimento_save"),
    path("locais-atendimento/<int:pk>/excluir/", views.local_atendimento_delete, name="local_atendimento_delete"),

    # Locais de embarque
    path("locais-embarque/", views.local_embarque_list, name="local_embarque_list"),
    path("locais-embarque/salvar/", views.local_embarque_save, name="local_embarque_create"),
    path("locais-embarque/<int:pk>/salvar/", views.local_embarque_save, name="local_embarque_save"),
    path("locais-embarque/<int:pk>/excluir/", views.local_embarque_delete, name="local_embarque_delete"),

    # Horários
    path("horarios/", views.horario_list, name="horario_list"),
    path("horarios/salvar/", views.horario_save, name="horario_create"),
    path("horarios/<int:pk>/salvar/", views.horario_save, name="horario_save"),
    path("horarios/<int:pk>/excluir/", views.horario_delete, name="horario_delete"),

    # Motoristas
    path("motoristas/", views.motorista_list, name="motorista_list"),
    path("motoristas/salvar/", views.motorista_save, name="motorista_create"),
    path("motoristas/<int:pk>/salvar/", views.motorista_save, name="motorista_save"),
    path("motoristas/<int:pk>/excluir/", views.motorista_delete, name="motorista_delete"),

    # Pacientes
    path("pacientes/", views.paciente_list, name="paciente_list"),
    path("pacientes/salvar/", views.paciente_save, name="paciente_create"),
    path("pacientes/<int:pk>/salvar/", views.paciente_save, name="paciente_save"),
    path("pacientes/<int:pk>/excluir/", views.paciente_delete, name="paciente_delete"),

    # Protocolos
    path("protocolos/", views.protocolo_list, name="protocolo_list"),
    path("protocolos/novo/", views.protocolo_create, name="protocolo_create"),
    path("protocolos/<int:pk>/editar/", views.protocolo_edit, name="protocolo_edit"),
    path("protocolos/<int:pk>/retirado/", views.protocolo_marcar_retirado, name="protocolo_retirado"),
    path("protocolos/<int:pk>/entregue/", views.protocolo_marcar_entregue, name="protocolo_entregue"),

    # Viagens
    path("viagens/", views.viagem_list, name="viagem_list"),
    path("viagens/nova/", views.viagem_create, name="viagem_create"),
    path("viagens/<int:pk>/", views.viagem_detail, name="viagem_detail"),
    path("viagens/<int:pk>/editar/", views.viagem_edit, name="viagem_edit"),
    path("viagens/<int:pk>/status/", views.viagem_status, name="viagem_status"),
    path("viagens/<int:pk>/passageiro/add/", views.viagem_add_passageiro, name="viagem_add_passageiro"),
    path("viagens/<int:pk>/passageiro/<int:passageiro_pk>/del/", views.viagem_remove_passageiro, name="viagem_remove_passageiro"),
]
