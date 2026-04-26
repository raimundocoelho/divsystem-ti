"""Resolve o tenant ativo a partir do usuário logado.

Replica o `ResolveTenant` do Laravel:
  - se o usuário tem `tenant_id` próprio: este é o tenant ativo.
  - se o usuário é Admin global (sem tenant_id) e há `admin_tenant_id` na sessão,
    usa esse para permitir que o admin "entre" em uma prefeitura específica.
"""
from django.utils.deprecation import MiddlewareMixin

from .threadlocal import clear_current_tenant, set_current_tenant


class ResolveTenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        clear_current_tenant()
        request.tenant = None

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return None

        tenant = None
        if user.tenant_id:
            tenant = user.tenant
        elif user.is_global_admin:
            admin_tenant_id = request.session.get("admin_tenant_id")
            if admin_tenant_id:
                from apps.core.models import Tenant
                tenant = Tenant.all_tenants.filter(pk=admin_tenant_id).first()

        if tenant is not None:
            set_current_tenant(tenant)
            request.tenant = tenant

        return None

    def process_response(self, request, response):
        clear_current_tenant()
        return response
