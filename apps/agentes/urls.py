from django.urls import path

from . import views

app_name = "agentes"

urlpatterns = [
    path("", views.AgenteListView.as_view(), name="list"),
    path("<int:pk>/", views.AgenteDetailView.as_view(), name="detail"),
    path("<int:pk>/editar/", views.AgenteUpdateView.as_view(), name="edit"),
    path("<int:pk>/excluir/", views.AgenteDeleteView.as_view(), name="delete"),
    path("<int:pk>/comando/", views.SendRemoteCommandView.as_view(), name="send_command"),
]
