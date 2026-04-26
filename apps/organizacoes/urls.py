from django.urls import path

from . import views

app_name = "organizacoes"

urlpatterns = [
    path("secretarias/", views.SecretariaListView.as_view(), name="secretaria_list"),
    path("secretarias/nova/", views.SecretariaCreateView.as_view(), name="secretaria_new"),
    path("secretarias/<int:pk>/editar/", views.SecretariaUpdateView.as_view(), name="secretaria_edit"),
    path("secretarias/<int:pk>/excluir/", views.SecretariaDeleteView.as_view(), name="secretaria_delete"),
    path("setores/", views.SetorListView.as_view(), name="setor_list"),
    path("setores/novo/", views.SetorCreateView.as_view(), name="setor_new"),
    path("setores/<int:pk>/editar/", views.SetorUpdateView.as_view(), name="setor_edit"),
    path("setores/<int:pk>/excluir/", views.SetorDeleteView.as_view(), name="setor_delete"),
]
