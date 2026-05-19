from django.urls import path

from . import site_policy_views, views

app_name = "agentes"

urlpatterns = [
    # --- Políticas de Sites (via agente) — porte do Laravel ---
    path("politicas/", site_policy_views.politica_list, name="politica_list"),
    path("politicas/nova/", site_policy_views.politica_create, name="politica_create"),
    path("politicas/<int:pk>/editar/", site_policy_views.politica_edit_modal, name="politica_edit"),
    path("politicas/<int:pk>/toggle-active/", site_policy_views.politica_toggle_active, name="politica_toggle_active"),
    path("politicas/<int:pk>/aplicar/", site_policy_views.politica_aplicar, name="politica_aplicar"),
    path("politicas/<int:pk>/delete/", site_policy_views.politica_delete, name="politica_delete"),
    path("politicas/<int:pk>/regras/", site_policy_views.politica_rules_modal, name="politica_rules_modal"),
    path("politicas/<int:pk>/regras/cat/<slug:slug>/toggle/", site_policy_views.politica_toggle_categoria, name="politica_toggle_categoria"),
    path("politicas/<int:pk>/regras/add/", site_policy_views.politica_add_regra, name="politica_add_regra"),
    path("politicas/<int:pk>/regras/<int:regra_pk>/del/", site_policy_views.politica_del_regra, name="politica_del_regra"),
    path("politicas/<int:pk>/atribuir/", site_policy_views.politica_assign_modal, name="politica_assign_modal"),
    path("politicas/<int:pk>/atribuir/<int:agent_pk>/toggle/", site_policy_views.politica_toggle_alvo, name="politica_toggle_alvo"),

    # --- Sites Bloqueados (lista legada simples) ---
    path("sites-bloqueados/", site_policy_views.sites_bloqueados, name="sites_bloqueados"),
    path("sites-bloqueados/salvar/", site_policy_views.sites_bloqueados_save, name="sites_bloqueados_save"),
    path("sites-bloqueados/<int:pk>/toggle/", site_policy_views.sites_bloqueados_toggle, name="sites_bloqueados_toggle"),
    path("sites-bloqueados/<int:pk>/excluir/", site_policy_views.sites_bloqueados_delete, name="sites_bloqueados_delete"),

    # --- Agentes (lista e detalhes) — já existente ---
    path("", views.AgenteListView.as_view(), name="list"),
    path("<int:pk>/", views.AgenteDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.AgenteUpdateView.as_view(), name="edit"),
    path("<int:pk>/excluir/", views.AgenteDeleteView.as_view(), name="delete"),
    path("<int:pk>/comando/", views.SendRemoteCommandView.as_view(), name="send_command"),
    path("<int:pk>/lotacao/", views.AgenteLotacaoUpdateView.as_view(), name="lotacao_update"),
]
