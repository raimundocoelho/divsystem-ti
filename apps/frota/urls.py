from django.urls import path

from . import views

app_name = "frota"

urlpatterns = [
    # Veículos
    path("veiculos/", views.veiculo_list, name="veiculo_list"),
    path("veiculos/salvar/", views.veiculo_save, name="veiculo_create"),
    path("veiculos/<int:pk>/salvar/", views.veiculo_save, name="veiculo_save"),

    # Diários de Bordo
    path("diarios-bordo/", views.diario_list, name="diario_list"),
    path("diarios-bordo/novo/", views.diario_create, name="diario_create"),
    path("diarios-bordo/<int:pk>/editar/", views.diario_edit, name="diario_edit"),
    path("diarios-bordo/last-km/", views.diario_last_km, name="diario_last_km"),

    # Relatórios
    path("relatorios/", views.relatorios, name="relatorios"),
]
