"""Usuário custom — espelha `App\\Models\\User` do Laravel.

- `tenant` é nullable porque admins globais (suporte da SABIO) não pertencem a uma
  prefeitura específica e podem alternar entre tenants pela sessão.
- `role` é hierárquico (Operador < Tecnico < Gestor < Admin) e usado no RBAC.
- `is_global_admin` é o equivalente ao `is_admin` do Laravel (acesso a todos os
  tenants). Não confundir com `role=ADMIN` (que é um admin de prefeitura).
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.permissions import UserRole, role_level


class UserManager(BaseUserManager):
    """Usa email como identificador único; replica o esquema do Laravel."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("É necessário informar um e-mail")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("role", UserRole.OPERADOR)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_global_admin", True)
        extra_fields.setdefault("role", UserRole.ADMIN)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser precisa is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser precisa is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    tenant = models.ForeignKey(
        "core.Tenant",
        on_delete=models.PROTECT,
        related_name="users",
        null=True,
        blank=True,
        db_index=True,
        help_text="Prefeitura à qual o usuário pertence. Vazio = admin global.",
    )

    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True, default="")
    role = models.CharField(
        max_length=16,
        choices=UserRole.choices,
        default=UserRole.OPERADOR,
    )
    is_global_admin = models.BooleanField(
        default=False,
        help_text="Acesso a todos os tenants (suporte SABIO).",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    two_factor_secret = models.TextField(blank=True, default="")
    two_factor_recovery_codes = models.TextField(blank=True, default="")

    date_joined = models.DateTimeField(default=timezone.now)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "role"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} <{self.email}>"

    def get_full_name(self) -> str:
        return self.name

    def get_short_name(self) -> str:
        return (self.name or self.email).split()[0]

    @property
    def initials(self) -> str:
        parts = [p for p in (self.name or "").split() if p]
        if not parts:
            return (self.email or "?")[:2].upper()
        if len(parts) == 1:
            return parts[0][:2].upper()
        return (parts[0][0] + parts[-1][0]).upper()

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN or self.is_global_admin

    def is_gestor(self) -> bool:
        return role_level(self.role) >= role_level(UserRole.GESTOR)

    def has_min_role(self, min_role) -> bool:
        if self.is_global_admin:
            return True
        return role_level(self.role) >= role_level(min_role)
