"""RBAC hierárquico — espelha `App\\Enums\\UserRole` do Laravel.

Operador(1) < Tecnico(2) < Gestor(3) < Admin(4)

Usar:
    from apps.core.permissions import UserRole, role_required

    @role_required(UserRole.GESTOR)
    def minha_view(request): ...

    user.has_min_role(UserRole.TECNICO)   # bool
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import models


class UserRole(models.TextChoices):
    OPERADOR = "operador", "Operador"
    TECNICO = "tecnico", "Técnico"
    GESTOR = "gestor", "Gestor"
    ADMIN = "admin", "Administrador"

    @property
    def level(self) -> int:
        return _ROLE_LEVELS[self.value]

    @property
    def color(self) -> str:
        return _ROLE_COLORS[self.value]


_ROLE_LEVELS = {"operador": 1, "tecnico": 2, "gestor": 3, "admin": 4}
_ROLE_COLORS = {
    "operador": "zinc",
    "tecnico": "amber",
    "gestor": "blue",
    "admin": "red",
}


@dataclass(frozen=True)
class _RoleSpec:
    """Comparável diretamente — para uso em ordering/comparações simples."""
    value: str
    level: int


def role_level(role) -> int:
    if isinstance(role, UserRole):
        return role.level
    if isinstance(role, str):
        return _ROLE_LEVELS.get(role, 0)
    return 0


def role_required(min_role: UserRole):
    """Exige que o usuário esteja autenticado e possua nível >= min_role."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated or not user.has_min_role(min_role):
                raise PermissionDenied("Acesso negado: papel insuficiente.")
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def admin_required(view_func):
    return role_required(UserRole.ADMIN)(view_func)
