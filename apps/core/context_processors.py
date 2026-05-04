from django.conf import settings


def tenant(request):
    available = []
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and getattr(user, "is_global_admin", False):
        from apps.core.models import Tenant
        available = list(
            Tenant.all_tenants.filter(active=True).order_by("name").only("id", "name", "code")
        )
    return {
        "current_tenant": getattr(request, "tenant", None),
        "available_tenants": available,
    }


def app_meta(request):
    return {
        "APP_NAME": "DivSystem",
        "APP_TAGLINE": "Gestão de TI Municipal",
        "APP_VERSION_AGENTE": getattr(settings, "AGENT_LATEST_VERSION", ""),
    }
