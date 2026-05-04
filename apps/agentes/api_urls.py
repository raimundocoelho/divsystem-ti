from django.urls import path

from . import api_views

app_name = "agent_api"

urlpatterns = [
    # /ping responde GET (público, healthcheck) e POST Bearer (agente reporta versão).
    # O agente C# 5.2.x bate POST /ping (sem barra). Manter os dois paths apontando
    # para a MESMA view evita o 405 silencioso.
    path("ping", api_views.ping_endpoint, name="ping"),
    path("ping/", api_views.ping_endpoint, name="ping_slash"),
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
