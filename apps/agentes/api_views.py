"""Endpoints da API do agente — `/api/v1/agent/*` (e legado `/api/agente/*`).

Esses endpoints são consumidos pelos agentes WPF/Service/Electron, não pelo
painel web. Autenticação via `AgentTokenAuthentication` (Bearer token).
"""
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.configuracoes.models import Setting
from apps.core.models import Tenant
from apps.organizacoes.models import Secretaria, Setor

from .authentication import AgentTokenAuthentication
from .models import AgentHeartbeat, AgentToken, RemoteCommand
from .serializers import (
    CommandResultSerializer,
    EnrollSerializer,
    HeartbeatInputSerializer,
)


# --- Health -----------------------------------------------------------------

@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def ping_public(request):
    return Response({"status": "ok", "timestamp": timezone.now().isoformat()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def ping_authenticated(request):
    agent: AgentToken = request.agent_token
    agent.last_ping_at = timezone.now()
    new_version = (request.data or {}).get("agent_version")
    if new_version and new_version != agent.agent_version:
        agent.agent_version = new_version
    agent.save(update_fields=["last_ping_at", "agent_version", "updated_at"])
    return Response({"ok": True})


# --- Heartbeat / Inventário -------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def heartbeat(request):
    agent: AgentToken = request.agent_token
    serializer = HeartbeatInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    AgentHeartbeat.objects.create(
        tenant_id=agent.tenant_id,
        agent_token=agent,
        machine_id=data["machine_id"],
        agent_version=data.get("agent_version", "") or "",
        hardware=data.get("hardware"),
        network=data.get("network"),
        system_info=data.get("system"),
        software=data.get("software"),
        peripherals=data.get("peripherals"),
        alerts=data.get("alerts"),
        collected_at=data.get("collected_at") or timezone.now(),
    )

    update_fields = ["last_seen_at", "updated_at"]
    agent.last_seen_at = timezone.now()
    if data.get("machine_id") and agent.machine_id != data["machine_id"]:
        agent.machine_id = data["machine_id"]
        update_fields.append("machine_id")
    hostname = data.get("hostname") or (data.get("network") or {}).get("hostname") or ""
    if hostname and agent.hostname != hostname:
        agent.hostname = hostname
        update_fields.append("hostname")
    if data.get("agent_version") and data["agent_version"] != agent.agent_version:
        agent.agent_version = data["agent_version"]
        update_fields.append("agent_version")
    agent.save(update_fields=update_fields)

    pending = list(
        RemoteCommand.objects.filter(agent_token=agent, status=RemoteCommand.Status.PENDING)
        .order_by("created_at")
    )
    now = timezone.now()
    for cmd in pending:
        cmd.status = RemoteCommand.Status.SENT
        cmd.sent_at = now
        cmd.save(update_fields=["status", "sent_at", "updated_at"])

    return Response({
        "message": "Heartbeat recebido",
        "machine_id": agent.machine_id,
        "pending_commands": [
            {"id": c.id, "command": c.command, "payload": c.payload or {}}
            for c in pending
        ],
        "agent_update": {
            "version": settings.AGENT_LATEST_VERSION,
            "url": settings.AGENT_UPDATE_URL,
            "sha256": settings.AGENT_UPDATE_SHA256,
        } if settings.AGENT_UPDATE_URL else None,
        "config": {
            "monitor_interval_seconds": 60,
            "collect_interval_minutes": 30,
        },
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def config_endpoint(request):
    agent: AgentToken = request.agent_token
    blocked = Setting.get("blocked_sites", default=[], tenant=agent.tenant) or []
    return Response({
        "blocked_sites": blocked,
        "monitor_interval_seconds": 60,
        "collect_interval_minutes": 30,
    })


# --- Enroll / Setup ---------------------------------------------------------

@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def enroll(request):
    serializer = EnrollSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    tenant = _resolve_tenant_by_code_or_master(
        enroll_code=data.get("enroll_code") or "",
        master_key=data.get("master_key") or "",
    )
    if tenant is None:
        return Response(
            {"error": "Código de enroll inválido."},
            status=status.HTTP_404_NOT_FOUND,
        )

    machine_id = data.get("machine_id") or ""
    name = data.get("name") or data.get("hostname") or "Agente"
    secretaria_id = data.get("secretaria_id")
    setor_id = data.get("setor_id")

    secretaria = None
    setor = None
    if secretaria_id:
        secretaria = Secretaria.all_tenants.filter(pk=secretaria_id, tenant_id=tenant.pk).first()
    if setor_id:
        setor = Setor.all_tenants.filter(pk=setor_id, tenant_id=tenant.pk).first()

    agent = None
    if machine_id:
        agent = AgentToken.all_tenants.filter(machine_id=machine_id).first()

    if agent:
        agent.tenant_id = tenant.pk
        agent.name = name
        agent.hostname = data.get("hostname") or agent.hostname
        if secretaria:
            agent.secretaria = secretaria
        if setor:
            agent.setor = setor
        agent.active = True
        if not agent.token:
            agent.token = AgentToken.generate_token()
        agent.save()
    else:
        agent = AgentToken.all_tenants.create(
            tenant_id=tenant.pk,
            name=name,
            token=AgentToken.generate_token(),
            machine_id=machine_id or None,
            hostname=data.get("hostname", "") or "",
            secretaria=secretaria,
            setor=setor,
            active=True,
        )

    return Response({
        "message": "Agente cadastrado com sucesso",
        "token": agent.token,
        "agent_id": agent.id,
    })


def _resolve_tenant_by_code_or_master(enroll_code: str, master_key: str):
    if enroll_code:
        tenant = (
            Tenant.all_tenants.filter(external_code=enroll_code, active=True).first()
            or Tenant.all_tenants.filter(code=enroll_code, active=True).first()
        )
        if tenant:
            return tenant
    if master_key:
        return Tenant.all_tenants.filter(master_key=master_key, active=True).first()
    return None


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def setup_validate_code(request, code: str):
    tenant = _resolve_tenant_by_code_or_master(code, "")
    if not tenant:
        return Response({"error": "Código não encontrado."}, status=status.HTTP_404_NOT_FOUND)
    return Response({"id": tenant.pk, "name": tenant.name})


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def setup_secretarias(request, code: str):
    tenant = _resolve_tenant_by_code_or_master(code, "")
    if not tenant:
        return Response({"error": "Código não encontrado."}, status=status.HTTP_404_NOT_FOUND)
    secretarias = (
        Secretaria.all_tenants.filter(tenant_id=tenant.pk, ativo=True)
        .order_by("nome")
        .values("id", "nome")
    )
    return Response([{"id": s["id"], "name": s["nome"]} for s in secretarias])


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def setup_setores(request, code: str, secretaria_id: int):
    tenant = _resolve_tenant_by_code_or_master(code, "")
    if not tenant:
        return Response({"error": "Código não encontrado."}, status=status.HTTP_404_NOT_FOUND)
    setores = (
        Setor.all_tenants.filter(tenant_id=tenant.pk, secretaria_id=secretaria_id, ativo=True)
        .order_by("nome")
        .values("id", "nome")
    )
    return Response([{"id": s["id"], "name": s["nome"]} for s in setores])


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def setup_resolve_master_key(request):
    master_key = (request.data or {}).get("master_key", "")
    expected = Setting.get("agent_master_key", default="", tenant=None) or ""
    if not master_key or master_key != expected:
        return Response({"ok": False, "error": "Chave inválida."}, status=403)
    tenants = Tenant.all_tenants.filter(active=True).values("id", "name", "code", "external_code")
    return Response({
        "ok": True,
        "tenants": [
            {
                "id": t["id"],
                "name": t["name"],
                "code": t["code"],
                "enroll_code": t["external_code"] or t["code"],
            }
            for t in tenants
        ],
    })


# --- Comandos ---------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def commands_pending(request):
    agent: AgentToken = request.agent_token
    pending = list(
        RemoteCommand.objects.filter(
            agent_token=agent,
            status__in=[RemoteCommand.Status.PENDING, RemoteCommand.Status.SENT],
        ).order_by("created_at")
    )
    now = timezone.now()
    for cmd in pending:
        if cmd.status == RemoteCommand.Status.PENDING:
            cmd.status = RemoteCommand.Status.SENT
            cmd.sent_at = now
            cmd.save(update_fields=["status", "sent_at", "updated_at"])
    return Response({
        "commands": [
            {
                "id": c.id,
                "command": c.command,
                "type": c.command,
                "payload": c.payload or {},
            }
            for c in pending
        ],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def command_result(request):
    serializer = CommandResultSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    agent: AgentToken = request.agent_token
    cmd = get_object_or_404(RemoteCommand, pk=data["command_id"], agent_token=agent)

    now = timezone.now()
    new_status = data["status"]
    if new_status == "running":
        cmd.status = RemoteCommand.Status.RUNNING
        cmd.executed_at = cmd.executed_at or now
    elif new_status in {"success", "completed"}:
        cmd.status = RemoteCommand.Status.SUCCESS
        cmd.completed_at = now
        if not cmd.executed_at:
            cmd.executed_at = now
    elif new_status == "failed":
        cmd.status = RemoteCommand.Status.FAILED
        cmd.completed_at = now
        if not cmd.executed_at:
            cmd.executed_at = now

    if data.get("output") is not None:
        cmd.output = data["output"]
    if data.get("error") is not None:
        cmd.error = data["error"]

    cmd.save()
    return Response({"ok": True, "id": cmd.id, "status": cmd.status})
