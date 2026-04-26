from django.conf import settings


def tenant(request):
    return {
        "current_tenant": getattr(request, "tenant", None),
    }


def app_meta(request):
    return {
        "APP_NAME": "DivSystem",
        "APP_TAGLINE": "Gestão de TI Municipal",
        "APP_VERSION_AGENTE": getattr(settings, "AGENT_LATEST_VERSION", ""),
    }
