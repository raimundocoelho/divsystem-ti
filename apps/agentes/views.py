from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from apps.core.permissions import UserRole
from apps.core.views_mixins import RoleRequiredMixin

from .forms import AgentTokenForm, SendCommandForm
from .models import AgentToken, RemoteCommand


class AgenteListView(RoleRequiredMixin, ListView):
    required_role = UserRole.GESTOR
    template_name = "agentes/agent_list.html"
    context_object_name = "agentes"
    paginate_by = 30

    def get_queryset(self):
        qs = AgentToken.objects.select_related("secretaria", "setor")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(name__icontains=q) | qs.filter(hostname__icontains=q)
        return qs.order_by("name")


class AgenteCreateView(RoleRequiredMixin, CreateView):
    required_role = UserRole.GESTOR
    model = AgentToken
    form_class = AgentTokenForm
    template_name = "agentes/agent_form.html"
    success_url = reverse_lazy("agentes:list")


class AgenteUpdateView(RoleRequiredMixin, UpdateView):
    required_role = UserRole.GESTOR
    model = AgentToken
    form_class = AgentTokenForm
    template_name = "agentes/agent_form.html"
    success_url = reverse_lazy("agentes:list")


class AgenteDetailView(RoleRequiredMixin, DetailView):
    required_role = UserRole.GESTOR
    model = AgentToken
    template_name = "agentes/agent_detail.html"
    context_object_name = "agente"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        agente = self.object
        ctx["latest_heartbeat"] = agente.heartbeats.order_by("-created_at").first()
        ctx["recent_commands"] = agente.remote_commands.order_by("-created_at")[:20]
        ctx["send_command_form"] = SendCommandForm()
        return ctx


class AgenteDeleteView(RoleRequiredMixin, DeleteView):
    required_role = UserRole.GESTOR
    model = AgentToken
    template_name = "agentes/agent_confirm_delete.html"
    success_url = reverse_lazy("agentes:list")


class SendRemoteCommandView(RoleRequiredMixin, View):
    required_role = UserRole.GESTOR

    def post(self, request, pk):
        agente = get_object_or_404(AgentToken, pk=pk)
        form = SendCommandForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Comando inválido.")
            return redirect("agentes:detail", pk=pk)

        cmd = form.cleaned_data["cmd_type"]
        payload_raw = form.cleaned_data.get("cmd_payload") or ""
        payload = {}
        if payload_raw:
            try:
                import json
                payload = json.loads(payload_raw)
            except (TypeError, ValueError):
                payload = {"raw": payload_raw}

        RemoteCommand.objects.create(
            tenant_id=agente.tenant_id,
            agent_token=agente,
            command=cmd,
            payload=payload,
            status=RemoteCommand.Status.PENDING,
            created_by=request.user,
        )
        messages.success(request, "Comando enfileirado para o agente.")
        return redirect("agentes:detail", pk=pk)
