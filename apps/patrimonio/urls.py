from django.urls import path

from . import views

app_name = "patrimonio"

urlpatterns = [
    path("", views.patrimonio_list, name="list"),
    path("novo/", views.patrimonio_create, name="create"),
    path("<int:pk>/", views.patrimonio_detail, name="detail"),
    path("<int:pk>/editar/", views.patrimonio_edit, name="edit"),
    path("<int:pk>/excluir/", views.patrimonio_delete, name="delete"),

    # Categorias MCASP
    path("categorias/", views.categoria_list, name="categoria_list"),
    path("categorias/salvar/", views.categoria_save, name="categoria_create"),
    path("categorias/<int:pk>/salvar/", views.categoria_save, name="categoria_save"),
    path("categorias/<int:pk>/excluir/", views.categoria_delete, name="categoria_delete"),

    # Locais
    path("locais/", views.local_list, name="local_list"),
    path("locais/salvar/", views.local_save, name="local_create"),
    path("locais/<int:pk>/salvar/", views.local_save, name="local_save"),
    path("locais/<int:pk>/excluir/", views.local_delete, name="local_delete"),
]
