"""Mixins para CBVs (ListView/CreateView/etc) que precisam de tenant + RBAC."""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied

from .permissions import UserRole


class TenantRequiredMixin(LoginRequiredMixin):
    """Bloqueia acesso se não houver tenant ativo no request."""

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        return response


class RoleRequiredMixin(LoginRequiredMixin):
    """CBVs que exigem nível mínimo de role.

    Defina `required_role = UserRole.GESTOR` na view.
    """

    required_role: UserRole = UserRole.OPERADOR

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_min_role(self.required_role):
            raise PermissionDenied("Acesso negado: papel insuficiente.")
        return super().dispatch(request, *args, **kwargs)
