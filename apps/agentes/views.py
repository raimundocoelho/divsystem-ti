from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DeleteView, DetailView, ListView, UpdateView, View

from apps.core.permissions import UserRole
from apps.core.views_mixins import RoleRequiredMixin
from apps.organizacoes.models import Secretaria, Setor

from .forms import AgentTokenForm, SendCommandForm
from .models import AgentToken, RemoteCommand


class AgenteListView(RoleRequiredMixin, ListView):
    required_role = UserRole.GESTOR
    template_name = "agentes/agent_list.html"
    context_object_name = "agentes"
    paginate_by = None  # tabela completa — counts e filtros sao client-friendly

    def _filters(self):
        get = self.request.GET
        return {
            "q": get.get("q", "").strip(),
            "secretaria": get.get("secretaria", "").strip() or None,
            "setor": get.get("setor", "").strip() or None,
        }

    def get_queryset(self):
        f = self._filters()
        qs = (
            AgentToken.objects
            .select_related("secretaria", "setor")
            .annotate(hb_total=Count("heartbeats", distinct=True))
        )
        if f["secretaria"]:
            qs = qs.filter(secretaria_id=f["secretaria"])
        if f["setor"]:
            qs = qs.filter(setor_id=f["setor"])
        if f["q"]:
            q = f["q"]
            qs = qs.filter(
                Q(hostname__icontains=q)
                | Q(name__icontains=q)
                | Q(machine_id__icontains=q)
                | Q(description__icontains=q)
            )
        return qs.order_by("-last_seen_at", "name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        f = self._filters()

        agentes = list(ctx["agentes"])

        # Counts derivados em Python (lista pequena, ~dezenas de agentes).
        ctx["online_count"] = sum(1 for a in agentes if a.online_status == "online")
        ctx["warning_count"] = sum(1 for a in agentes if a.online_status == "warning")
        ctx["offline_count"] = sum(1 for a in agentes if a.online_status in ("offline", "inativo"))
        ctx["outdated_count"] = sum(1 for a in agentes if a.is_outdated())

        ctx["latest_version"] = AgentToken.latest_available_version()

        # Listas pros selects (escopo do tenant respeitado por TenantOwnedModel).
        ctx["secretarias_list"] = Secretaria.objects.filter(ativo=True).order_by("nome")
        setores = Setor.objects.filter(ativo=True)
        if f["secretaria"]:
            setores = setores.filter(secretaria_id=f["secretaria"])
        ctx["setores_list"] = setores.order_by("nome")

        ctx["filter_q"] = f["q"]
        ctx["filter_secretaria"] = f["secretaria"] or ""
        ctx["filter_setor"] = f["setor"] or ""
        return ctx


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
        # Pega o ultimo heartbeat com algum dado (hardware/network/system_info).
        # Heartbeats vazios ocorrem quando o collector teve erro.
        ctx["latest_heartbeat"] = (
            agente.heartbeats
            .filter(
                Q(hardware__isnull=False)
                | Q(network__isnull=False)
                | Q(system_info__isnull=False)
            )
            .order_by("-created_at")
            .first()
        )
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
            messages.error(request, "Comando invalido.")
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
