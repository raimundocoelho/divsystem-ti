from django.urls import path

from . import views

app_name = "configuracoes"

urlpatterns = [
    path("", views.SettingListView.as_view(), name="list"),
    path("nova/", views.SettingCreateView.as_view(), name="new"),
    path("<int:pk>/editar/", views.SettingUpdateView.as_view(), name="edit"),
    path("<int:pk>/excluir/", views.SettingDeleteView.as_view(), name="delete"),
]
