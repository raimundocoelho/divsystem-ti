from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.permissions import UserRole
from apps.core.views_mixins import RoleRequiredMixin

from .forms import SecretariaForm, SetorForm
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
