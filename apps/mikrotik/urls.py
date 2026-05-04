from django.urls import path

from apps.mikrotik import views

app_name = "mikrotik"

urlpatterns = [
    path("", views.equipamento_list, name="list"),
    path("novo/", views.equipamento_create, name="create"),
    # Tenant-level Políticas de Sites + Sites Bloqueados (NEW UX)
    path("politicas/", views.tenant_politica_list, name="tenant_politica_list"),
    path("politicas/nova/", views.tenant_politica_create, name="tenant_politica_create"),
    path("politicas/<int:pk>/editar/", views.tenant_politica_edit, name="tenant_politica_edit"),
    path("politicas/<int:pk>/toggle-active/", views.tenant_politica_toggle_active, name="tenant_politica_toggle_active"),
    path("politicas/<int:pk>/aplicar/", views.tenant_politica_aplicar, name="tenant_politica_aplicar"),
    path("politicas/<int:pk>/remover-router/", views.tenant_politica_remover_router, name="tenant_politica_remover_router"),
    path("politicas/<int:pk>/delete/", views.tenant_politica_delete, name="tenant_politica_delete"),
    path("politicas/<int:pk>/regras/", views.tenant_politica_rules_modal, name="tenant_politica_rules_modal"),
    path("politicas/<int:pk>/regras/cat/<slug:slug>/toggle/", views.tenant_politica_toggle_categoria, name="tenant_politica_toggle_categoria"),
    path("politicas/<int:pk>/regras/add/", views.tenant_politica_add_regra_htmx, name="tenant_politica_add_regra_htmx"),
    path("politicas/<int:pk>/regras/<int:regra_pk>/del/", views.tenant_politica_del_regra_htmx, name="tenant_politica_del_regra_htmx"),
    path("politicas/<int:pk>/atribuir/", views.tenant_politica_assign_modal, name="tenant_politica_assign_modal"),
    path("politicas/<int:pk>/atribuir/<int:device_pk>/toggle/", views.tenant_politica_toggle_alvo_htmx, name="tenant_politica_toggle_alvo_htmx"),
    path("sites-bloqueados/", views.tenant_sites_bloqueados, name="tenant_sites_bloqueados"),

    path("<slug:slug>/", views.equipamento_detail, name="detail"),
    path("<slug:slug>/provisionar/", views.equipamento_provisionar, name="provisionar"),
    path("<slug:slug>/script/", views.equipamento_script, name="script"),
    path("<slug:slug>/comando/", views.equipamento_enviar_comando, name="enviar_comando"),
    path("<slug:slug>/ping/", views.equipamento_ping, name="ping"),
    # Devices
    path("<slug:slug>/devices/", views.device_list, name="device_list"),
    path("<slug:slug>/devices/novo/", views.device_create, name="device_create"),
    path("<slug:slug>/devices/<int:pk>/editar/", views.device_edit, name="device_edit"),
    path("<slug:slug>/devices/<int:pk>/sync/", views.device_sync, name="device_sync"),
    path("<slug:slug>/devices/<int:pk>/excluir/", views.device_delete, name="device_delete"),
    path("<slug:slug>/discovery/", views.equipamento_discovery, name="discovery"),
    path("<slug:slug>/sync-all/", views.equipamento_sync_all, name="sync_all"),
    # Rogues
    path("<slug:slug>/rogues/", views.rogue_list, name="rogue_list"),
    path("<slug:slug>/rogues/<int:pk>/acao/", views.rogue_action, name="rogue_action"),
    # Políticas
    path("<slug:slug>/politicas/", views.politica_list, name="politica_list"),
    path("<slug:slug>/politicas/nova/", views.politica_create, name="politica_create"),
    path("<slug:slug>/politicas/<int:pk>/", views.politica_detail, name="politica_detail"),
    path("<slug:slug>/politicas/<int:pk>/dominio/add/", views.politica_add_dominio, name="politica_add_dominio"),
    path("<slug:slug>/politicas/<int:pk>/dominio/<int:regra_pk>/del/", views.politica_del_dominio, name="politica_del_dominio"),
    path("<slug:slug>/politicas/<int:pk>/alvo/add/", views.politica_add_alvo, name="politica_add_alvo"),
    path("<slug:slug>/politicas/<int:pk>/alvo/<int:alvo_pk>/del/", views.politica_del_alvo, name="politica_del_alvo"),
    path("<slug:slug>/politicas/<int:pk>/aplicar/", views.politica_aplicar, name="politica_aplicar"),
    path("<slug:slug>/politicas/<int:pk>/remover-router/", views.politica_remover_router, name="politica_remover_router"),
    path("<slug:slug>/politicas/<int:pk>/delete/", views.politica_delete, name="politica_delete"),
]
