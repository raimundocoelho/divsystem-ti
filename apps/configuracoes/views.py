from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.core.permissions import UserRole
from apps.core.views_mixins import RoleRequiredMixin

from .forms import SettingForm
from .models import Setting


class SettingListView(RoleRequiredMixin, ListView):
    required_role = UserRole.GESTOR
    template_name = "configuracoes/setting_list.html"
    context_object_name = "settings"
    paginate_by = 50

    def get_queryset(self):
        return Setting.objects.order_by("key")


class SettingCreateView(RoleRequiredMixin, CreateView):
    required_role = UserRole.ADMIN
    model = Setting
    form_class = SettingForm
    template_name = "configuracoes/setting_form.html"
    success_url = reverse_lazy("configuracoes:list")

    def form_valid(self, form):
        messages.success(self.request, f"Configuração '{form.instance.key}' criada.")
        return super().form_valid(form)


class SettingUpdateView(RoleRequiredMixin, UpdateView):
    required_role = UserRole.ADMIN
    model = Setting
    form_class = SettingForm
    template_name = "configuracoes/setting_form.html"
    success_url = reverse_lazy("configuracoes:list")

    def form_valid(self, form):
        messages.success(self.request, "Configuração atualizada.")
        return super().form_valid(form)


class SettingDeleteView(RoleRequiredMixin, DeleteView):
    required_role = UserRole.ADMIN
    model = Setting
    template_name = "configuracoes/setting_confirm_delete.html"
    success_url = reverse_lazy("configuracoes:list")
