from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    UserChangeForm as DjangoUserChangeForm,
    UserCreationForm as DjangoUserCreationForm,
)
from django.utils.translation import gettext_lazy as _

from apps.core.permissions import UserRole

from .models import User


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="E-mail",
        widget=forms.EmailInput(attrs={"class": "input", "autofocus": "autofocus", "autocomplete": "email"}),
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": "input", "autocomplete": "current-password"}),
    )
    remember = forms.BooleanField(required=False, label="Manter conectado")

    error_messages = {
        "invalid_login": _("E-mail ou senha incorretos."),
        "inactive": _("Esta conta está desativada."),
        "tenant_inactive": _("Acesso da sua prefeitura está suspenso. Fale com o suporte."),
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        password = self.cleaned_data.get("password")

        if email and password:
            user = authenticate(self.request, username=email, password=password)
            if user is None:
                raise forms.ValidationError(self.error_messages["invalid_login"], code="invalid_login")
            if not user.is_active:
                raise forms.ValidationError(self.error_messages["inactive"], code="inactive")
            if user.tenant_id and not user.tenant.active:
                raise forms.ValidationError(
                    self.error_messages["tenant_inactive"], code="tenant_inactive"
                )
            self.user_cache = user
        return self.cleaned_data

    def get_user(self):
        return self.user_cache


class UserCreationForm(DjangoUserCreationForm):
    class Meta:
        model = User
        fields = ("email", "name", "tenant", "role", "is_global_admin", "is_active")


class UserChangeForm(DjangoUserChangeForm):
    class Meta:
        model = User
        fields = (
            "email", "name", "avatar_url", "tenant", "role",
            "is_global_admin", "is_active", "is_staff",
        )


class UserAdminForm(forms.ModelForm):
    """Form para CRUD de usuários no painel admin do tenant."""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "input"}),
        required=False,
        label="Senha (deixe em branco para manter)",
    )

    class Meta:
        model = User
        fields = ("name", "email", "role", "tenant", "avatar_url", "is_active")
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "autofocus": "autofocus"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
            "role": forms.Select(attrs={"class": "input"}),
            "tenant": forms.Select(attrs={"class": "input"}),
            "avatar_url": forms.URLInput(attrs={"class": "input"}),
        }

    def __init__(self, *args, request_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.request_user = request_user
        if request_user and not request_user.is_global_admin:
            # Tenant fica fixo no tenant do usuário logado
            self.fields["tenant"].queryset = self.fields["tenant"].queryset.filter(pk=request_user.tenant_id)
            self.fields["tenant"].initial = request_user.tenant_id
            self.fields["tenant"].disabled = True
            # Não permite criar/editar admin global
            self.fields["role"].choices = [c for c in UserRole.choices if c[0] != UserRole.ADMIN.value]

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("name", "email", "avatar_url")
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
            "avatar_url": forms.URLInput(attrs={"class": "input"}),
        }


class PasswordChangeMiniForm(forms.Form):
    current = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}), label="Senha atual")
    new = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}), label="Nova senha", min_length=8)
    confirm = forms.CharField(widget=forms.PasswordInput(attrs={"class": "input"}), label="Confirmar nova senha")

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        if not self.user.check_password(data.get("current") or ""):
            self.add_error("current", "Senha atual incorreta.")
        if data.get("new") and data.get("new") != data.get("confirm"):
            self.add_error("confirm", "A confirmação não coincide.")
        return data
