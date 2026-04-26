from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


urlpatterns = [
    path("admin/django/", admin.site.urls),
    path("", include(("apps.dashboard.urls", "dashboard"), namespace="dashboard")),
    path("contas/", include(("apps.accounts.urls", "accounts"), namespace="accounts")),
    path(
        "admin/organizacoes/",
        include(("apps.organizacoes.urls", "organizacoes"), namespace="organizacoes"),
    ),
    path(
        "admin/configuracoes/",
        include(("apps.configuracoes.urls", "configuracoes"), namespace="configuracoes"),
    ),
    path(
        "admin/agentes/",
        include(("apps.agentes.urls", "agentes"), namespace="agentes"),
    ),
    path(
        "api/v1/agent/",
        include(("apps.agentes.api_urls", "agent_api"), namespace="agent_api"),
    ),
    path(
        "api/agente/",
        include(("apps.agentes.api_urls", "agent_api"), namespace="agent_api_legacy"),
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
