from django.urls import path

from . import api_views

app_name = "agent_api"

urlpatterns = [
    path("ping", api_views.ping_public, name="ping_public"),
    path("ping/", api_views.ping_authenticated, name="ping_auth"),
    path("heartbeat", api_views.heartbeat, name="heartbeat"),
    path("config", api_views.config_endpoint, name="config"),
    path("enroll", api_views.enroll, name="enroll"),
    path("commands/pending", api_views.commands_pending, name="commands_pending"),
    path("command-result", api_views.command_result, name="command_result"),
    path("setup/resolve-master-key", api_views.setup_resolve_master_key, name="setup_master_key"),
    path("setup/validate/<str:code>", api_views.setup_validate_code, name="setup_validate"),
    path("setup/<str:code>/secretarias", api_views.setup_secretarias, name="setup_secretarias"),
    path("setup/<str:code>/secretaria/<int:secretaria_id>/setores", api_views.setup_setores, name="setup_setores"),
]
