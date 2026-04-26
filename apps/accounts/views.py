from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, ListView, UpdateView, DeleteView, View

from apps.core.models import Tenant
from apps.core.permissions import UserRole
from apps.core.views_mixins import RoleRequiredMixin

from .forms import LoginForm, PasswordChangeMiniForm, ProfileForm, UserAdminForm
from .models import User


class LoginView(View):
    template_name = "accounts/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("dashboard:home")
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            user.last_login_at = timezone.now()
            user.save(update_fields=["last_login_at"])
            if not form.cleaned_data.get("remember"):
                request.session.set_expiry(0)
            next_url = request.GET.get("next") or request.POST.get("next") or reverse("dashboard:home")
            return HttpResponseRedirect(next_url)
        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    def get(self, request):
        return self.post(request)

    def post(self, request):
        logout(request)
        messages.info(request, "Você saiu da conta.")
        return redirect("accounts:login")


@login_required
def perfil(request):
    user = request.user
    if request.method == "POST" and request.POST.get("form") == "profile":
        form = ProfileForm(request.POST, instance=user)
        password_form = PasswordChangeMiniForm(user=user)
        if form.is_valid():
            form.save()
            messages.success(request, "Perfil atualizado.")
            return redirect("accounts:perfil")
    elif request.method == "POST" and request.POST.get("form") == "password":
        form = ProfileForm(instance=user)
        password_form = PasswordChangeMiniForm(request.POST, user=user)
        if password_form.is_valid():
            user.set_password(password_form.cleaned_data["new"])
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Senha alterada.")
            return redirect("accounts:perfil")
    else:
        form = ProfileForm(instance=user)
        password_form = PasswordChangeMiniForm(user=user)
    return render(
        request,
        "accounts/perfil.html",
        {"form": form, "password_form": password_form},
    )


# --- CRUD de usuários (admin do tenant) -------------------------------------

class UsuarioListView(RoleRequiredMixin, ListView):
    required_role = UserRole.GESTOR
    template_name = "accounts/usuario_list.html"
    context_object_name = "usuarios"
    paginate_by = 25

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.all() if user.is_global_admin else User.objects.all()
        # Filtro por tenant
        if not user.is_global_admin:
            qs = qs.filter(tenant_id=user.tenant_id)
        elif self.request.tenant:
            qs = qs.filter(tenant=self.request.tenant)

        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q))
        role = self.request.GET.get("role")
        if role:
            qs = qs.filter(role=role)
        return qs.select_related("tenant").order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["role_filter"] = self.request.GET.get("role", "")
        ctx["roles"] = UserRole.choices
        return ctx


class UsuarioCreateView(RoleRequiredMixin, CreateView):
    required_role = UserRole.GESTOR
    model = User
    form_class = UserAdminForm
    template_name = "accounts/usuario_form.html"
    success_url = reverse_lazy("accounts:usuarios")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request_user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = form.save(commit=False)
        if not self.request.user.is_global_admin:
            user.tenant_id = self.request.user.tenant_id
        if not user.password:
            user.set_unusable_password()
        password = form.cleaned_data.get("password")
        if password:
            user.set_password(password)
        else:
            # senha provisória
            import secrets
            user.set_password(secrets.token_urlsafe(12))
        user.save()
        messages.success(self.request, f"Usuário '{user.name}' criado.")
        return redirect(self.success_url)


class UsuarioUpdateView(RoleRequiredMixin, UpdateView):
    required_role = UserRole.GESTOR
    model = User
    form_class = UserAdminForm
    template_name = "accounts/usuario_form.html"
    success_url = reverse_lazy("accounts:usuarios")

    def get_queryset(self):
        qs = User.objects.all()
        if not self.request.user.is_global_admin:
            qs = qs.filter(tenant_id=self.request.user.tenant_id)
        return qs

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request_user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Usuário atualizado.")
        return super().form_valid(form)


class UsuarioDeleteView(RoleRequiredMixin, DeleteView):
    required_role = UserRole.GESTOR
    model = User
    template_name = "accounts/usuario_confirm_delete.html"
    success_url = reverse_lazy("accounts:usuarios")

    def get_queryset(self):
        qs = User.objects.all()
        if not self.request.user.is_global_admin:
            qs = qs.filter(tenant_id=self.request.user.tenant_id)
        return qs.exclude(pk=self.request.user.pk)


# --- Tenant switcher (admin global) -----------------------------------------

class SelecionarTenantView(LoginRequiredMixin, View):
    """Permite ao admin global escolher em qual tenant operar."""

    def get(self, request):
        if not request.user.is_global_admin:
            messages.error(request, "Apenas administradores globais.")
            return redirect("dashboard:home")
        tenants = Tenant.all_tenants.order_by("name")
        return render(request, "accounts/tenant_select.html", {"tenants": tenants})

    def post(self, request):
        if not request.user.is_global_admin:
            return redirect("dashboard:home")
        tenant_id = request.POST.get("tenant_id")
        if tenant_id:
            request.session["admin_tenant_id"] = int(tenant_id)
            messages.success(request, "Tenant selecionado.")
        else:
            request.session.pop("admin_tenant_id", None)
            messages.info(request, "Modo global ativado.")
        return redirect(request.POST.get("next") or "dashboard:home")
