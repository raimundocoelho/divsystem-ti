from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.models import Tenant
from apps.core.permissions import UserRole
from apps.core.views_mixins import RoleRequiredMixin

from .forms import SecretariaForm, SetorForm, TenantForm
from .models import Secretaria, Setor


# --- Secretarias ------------------------------------------------------------

class SecretariaListView(RoleRequiredMixin, ListView):
    required_role = UserRole.GESTOR
    template_name = "organizacoes/secretaria_list.html"
    context_object_name = "secretarias"
    paginate_by = 30

    def get_queryset(self):
        qs = Secretaria.objects.annotate(setores_count=Count("setores"))
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(codigo__icontains=q) | Q(responsavel__icontains=q))
        ativo = self.request.GET.get("ativo")
        if ativo in {"1", "0"}:
            qs = qs.filter(ativo=ativo == "1")
        return qs.order_by("nome")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["ativo"] = self.request.GET.get("ativo", "")
        return ctx


class SecretariaCreateView(RoleRequiredMixin, CreateView):
    required_role = UserRole.GESTOR
    model = Secretaria
    form_class = SecretariaForm
    template_name = "organizacoes/secretaria_form.html"
    success_url = reverse_lazy("organizacoes:secretaria_list")

    def form_valid(self, form):
        messages.success(self.request, f"Secretaria '{form.instance.nome}' criada.")
        return super().form_valid(form)


class SecretariaUpdateView(RoleRequiredMixin, UpdateView):
    required_role = UserRole.GESTOR
    model = Secretaria
    form_class = SecretariaForm
    template_name = "organizacoes/secretaria_form.html"
    success_url = reverse_lazy("organizacoes:secretaria_list")

    def form_valid(self, form):
        messages.success(self.request, "Secretaria atualizada.")
        return super().form_valid(form)


class SecretariaDeleteView(RoleRequiredMixin, DeleteView):
    required_role = UserRole.GESTOR
    model = Secretaria
    template_name = "organizacoes/secretaria_confirm_delete.html"
    success_url = reverse_lazy("organizacoes:secretaria_list")

    def form_valid(self, form):
        messages.success(self.request, "Secretaria excluída.")
        return super().form_valid(form)


# --- Setores ----------------------------------------------------------------

class SetorListView(RoleRequiredMixin, ListView):
    required_role = UserRole.GESTOR
    template_name = "organizacoes/setor_list.html"
    context_object_name = "setores"
    paginate_by = 30

    def get_queryset(self):
        qs = Setor.objects.select_related("secretaria")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(nome__icontains=q) | Q(localizacao__icontains=q) | Q(responsavel__icontains=q))
        secretaria_id = self.request.GET.get("secretaria")
        if secretaria_id:
            qs = qs.filter(secretaria_id=secretaria_id)
        return qs.order_by("nome")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["secretaria_id"] = self.request.GET.get("secretaria", "")
        ctx["secretarias"] = Secretaria.objects.filter(ativo=True).order_by("nome")
        return ctx


class SetorCreateView(RoleRequiredMixin, CreateView):
    required_role = UserRole.GESTOR
    model = Setor
    form_class = SetorForm
    template_name = "organizacoes/setor_form.html"
    success_url = reverse_lazy("organizacoes:setor_list")

    def form_valid(self, form):
        messages.success(self.request, f"Setor '{form.instance.nome}' criado.")
        return super().form_valid(form)


class SetorUpdateView(RoleRequiredMixin, UpdateView):
    required_role = UserRole.GESTOR
    model = Setor
    form_class = SetorForm
    template_name = "organizacoes/setor_form.html"
    success_url = reverse_lazy("organizacoes:setor_list")


class SetorDeleteView(RoleRequiredMixin, DeleteView):
    required_role = UserRole.GESTOR
    model = Setor
    template_name = "organizacoes/setor_confirm_delete.html"
    success_url = reverse_lazy("organizacoes:setor_list")


# --- Tenants (Organizações) — admin global ---------------------------------


class GlobalAdminRequiredMixin(LoginRequiredMixin):
    """Apenas admins globais (suporte SABIO) podem gerenciar tenants."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not getattr(request.user, "is_global_admin", False):
            raise PermissionDenied("Apenas administradores globais.")
        return super().dispatch(request, *args, **kwargs)


class TenantListView(GlobalAdminRequiredMixin, ListView):
    template_name = "organizacoes/tenant_list.html"
    context_object_name = "tenants"

    def get_queryset(self):
        qs = Tenant.all_tenants.annotate(
            users_count=Count("users", distinct=True),
            agent_tokens_count=Count("agenttokens", distinct=True),
            secretarias_count=Count("secretarias", distinct=True),
        )
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(code__icontains=q)
                | Q(cnpj__icontains=q)
                | Q(city__icontains=q)
            )
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        active_id = self.request.session.get("admin_tenant_id")
        ctx["active_tenant_id"] = active_id
        ctx["active_tenant"] = (
            Tenant.all_tenants.filter(pk=active_id).first() if active_id else None
        )
        ctx["just_created_id"] = self.request.session.pop("tenant_just_created", None)
        return ctx


class TenantCreateView(GlobalAdminRequiredMixin, CreateView):
    model = Tenant
    form_class = TenantForm
    template_name = "organizacoes/tenant_form.html"
    success_url = reverse_lazy("organizacoes:tenant_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session["tenant_just_created"] = self.object.pk
        messages.success(self.request, f"Organização '{self.object.name}' criada.")
        return response


class TenantUpdateView(GlobalAdminRequiredMixin, UpdateView):
    model = Tenant
    form_class = TenantForm
    template_name = "organizacoes/tenant_form.html"
    success_url = reverse_lazy("organizacoes:tenant_list")

    def get_queryset(self):
        return Tenant.all_tenants.all()

    def form_valid(self, form):
        messages.success(self.request, "Organização atualizada.")
        return super().form_valid(form)


class TenantToggleActiveView(GlobalAdminRequiredMixin, View):
    def post(self, request, pk):
        tenant = get_object_or_404(Tenant.all_tenants, pk=pk)
        tenant.active = not tenant.active
        tenant.save(update_fields=["active", "updated_at"])
        messages.success(
            request,
            f"Organização '{tenant.name}' {'ativada' if tenant.active else 'desativada'}.",
        )
        return redirect("organizacoes:tenant_list")


class TenantDeleteView(GlobalAdminRequiredMixin, View):
    def post(self, request, pk):
        tenant = (
            Tenant.all_tenants.annotate(
                users_count=Count("users", distinct=True),
                agent_tokens_count=Count("agenttokens", distinct=True),
            )
            .filter(pk=pk)
            .first()
        )
        if not tenant:
            messages.error(request, "Organização não encontrada.")
            return redirect("organizacoes:tenant_list")
        if tenant.users_count or tenant.agent_tokens_count:
            messages.error(
                request,
                "Não é possível excluir: existem usuários ou agentes vinculados.",
            )
            return redirect("organizacoes:tenant_list")
        nome = tenant.name
        tenant.delete()
        messages.success(request, f"Organização '{nome}' excluída.")
        return redirect("organizacoes:tenant_list")


class TenantSelectView(GlobalAdminRequiredMixin, View):
    """Define o tenant ativo na sessão (admin global)."""

    def post(self, request, pk=None):
        if pk:
            tenant = get_object_or_404(Tenant.all_tenants, pk=pk)
            request.session["admin_tenant_id"] = tenant.pk
            messages.success(request, f"Filtrando por {tenant.name}.")
        else:
            request.session.pop("admin_tenant_id", None)
            messages.info(request, "Filtro de organização removido.")
        next_url = request.POST.get("next") or reverse("organizacoes:tenant_list")
        return HttpResponseRedirect(next_url)
