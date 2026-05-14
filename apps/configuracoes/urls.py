from django.urls import path

from . import views

app_name = "configuracoes"

urlpatterns = [
    # Home: cards (wallpaper + futuros)
    path("", views.ConfiguracoesHomeView.as_view(), name="list"),

    # Wallpaper
    path("wallpaper/upload/", views.WallpaperUploadView.as_view(), name="wallpaper_upload"),
    path("wallpaper/<int:pk>/reapply/", views.WallpaperReapplyView.as_view(), name="wallpaper_reapply"),

    # Setting CRUD (chave-valor — admin avancado)
    path("settings/", views.SettingListView.as_view(), name="setting_list"),
    path("settings/nova/", views.SettingCreateView.as_view(), name="setting_new"),
    path("settings/<int:pk>/editar/", views.SettingUpdateView.as_view(), name="setting_edit"),
    path("settings/<int:pk>/excluir/", views.SettingDeleteView.as_view(), name="setting_delete"),
]
