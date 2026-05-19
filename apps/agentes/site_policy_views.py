"""Views da UI de Políticas de Sites e Sites Bloqueados (via agente).

Porte 1:1 dos componentes Livewire `monitoramento.politicas-sites` e
`monitoramento.sites-bloqueados` do projeto Laravel original.
"""
from __future__ import annotations

import re
from typing import Iterable

from django.contrib import messages
from django.db.models import Count, Q
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.core.permissions import UserRole, role_required

from .models import (
    AgentToken,
    BlockedSite,
    RemoteCommand,
    SitePolicy,
    SiteRule,
    WorkstationPolicy,
)
from .site_categories import SITE_CATEGORIES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_domain(raw: str) -> str:
    d = (raw or "").strip().lower()
    d = re.sub(r"^https?://", "", d)
    return d.rstrip("/")


def _agent_ids_affected_by_policy(policy: SitePolicy) -> list[int]:
    if policy.is_global:
        qs = AgentToken.objects.filter(active=True)
        if policy.tenant_id:
            qs = qs.filter(Q(tenant_id=policy.tenant_id) | Q(tenant__isnull=True))
        return list(qs.values_list("id", flat=True))

    return list(
        WorkstationPolicy.objects.filter(site_policy=policy).values_list(
            "agent_token_id", flat=True
        )
    )


def _enqueue_apply_policies(agent_ids: Iterable[int], created_by=None) -> None:
    """Para cada agente, enfileira um RemoteCommand `apply_policies` (idempotente)."""
    for agent_id in set(agent_ids):
        already = RemoteCommand.objects.filter(
            agent_token_id=agent_id,
            command="apply_policies",
            status=RemoteCommand.Status.PENDING,
        ).exists()
        if already:
            continue
        RemoteCommand.objects.create(
            agent_token_id=agent_id,
            command="apply_policies",
            payload=None,
            status=RemoteCommand.Status.PENDING,
            created_by=created_by,
        )


def _enqueue_apply_for_policy(policy: SitePolicy, user) -> None:
    _enqueue_apply_policies(_agent_ids_affected_by_policy(policy), created_by=user)


# ---------------------------------------------------------------------------
# Políticas de Sites — listagem / CRUD
# ---------------------------------------------------------------------------

@role_required(UserRole.GESTOR)
def politica_list(request):
    busca = request.GET.get("q", "").strip()
    qs = SitePolicy.objects.annotate(
        rules_count=Count("rules", distinct=True),
        agents_count=Count("workstation_policies", distinct=True),
    ).select_related("created_by").order_by("-created_at")
    if busca:
        qs = qs.filter(Q(name__icontains=busca) | Q(description__icontains=busca))

    return render(request, "agentes/site_policies/list.html", {
        "politicas": qs,
        "busca": busca,
    })


@role_required(UserRole.GESTOR)
@require_POST
def politica_create(request):
    name = (request.POST.get("name") or "").strip()
    description = (request.POST.get("description") or "").strip()
    is_global = bool(request.POST.get("is_global"))
    if not name:
        messages.error(request, "Informe o nome da política.")
        return redirect("agentes:politica_list")
    policy = SitePolicy.objects.create(
        name=name[:100],
        description=description[:500],
        is_global=is_global,
        active=True,
        created_by=request.user,
    )
    _enqueue_apply_for_policy(policy, request.user)
    messages.success(request, f'Política "{policy.name}" criada.')
    return redirect("agentes:politica_list")


@role_required(UserRole.GESTOR)
def politica_edit_modal(request, pk: int):
    """GET: HTMX-modal com form de edição.

    POST: salva. Tanto GET quanto POST passam pelo mesmo handler pra simplificar.
    """
    policy = get_object_or_404(SitePolicy, pk=pk)
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        if not name:
            messages.error(request, "Informe o nome da política.")
            return redirect("agentes:politica_list")
        policy.name = name[:100]
        policy.description = (request.POST.get("description") or "").strip()[:500]
        policy.is_global = bool(request.POST.get("is_global"))
        policy.save(update_fields=["name", "description", "is_global", "updated_at"])
        _enqueue_apply_for_policy(policy, request.user)
        messages.success(request, "Política atualizada.")
        return redirect("agentes:politica_list")
    return render(request, "agentes/site_policies/_edit_modal.html", {"p": policy})


@role_required(UserRole.GESTOR)
@require_POST
def politica_toggle_active(request, pk: int):
    policy = get_object_or_404(SitePolicy, pk=pk)
    policy.active = not policy.active
    policy.save(update_fields=["active", "updated_at"])
    _enqueue_apply_for_policy(policy, request.user)
    return redirect("agentes:politica_list")


@role_required(UserRole.GESTOR)
@require_POST
def politica_delete(request, pk: int):
    policy = get_object_or_404(SitePolicy, pk=pk)
    affected = _agent_ids_affected_by_policy(policy)
    name = policy.name
    policy.delete()
    _enqueue_apply_policies(affected, created_by=request.user)
    messages.success(request, f'Política "{name}" removida.')
    return redirect("agentes:politica_list")


@role_required(UserRole.GESTOR)
@require_POST
def politica_aplicar(request, pk: int):
    """Botão 'Aplicar' — força reenvio do apply_policies, mesmo se já houver pendente."""
    policy = get_object_or_404(SitePolicy, pk=pk)
    for agent_id in _agent_ids_affected_by_policy(policy):
        RemoteCommand.objects.create(
            agent_token_id=agent_id,
            command="apply_policies",
            payload=None,
            status=RemoteCommand.Status.PENDING,
            created_by=request.user,
        )
    messages.success(request, "Comando apply_policies enfileirado para os agentes alvo.")
    return redirect("agentes:politica_list")


# ---------------------------------------------------------------------------
# Editor de regras (categorias + individuais) — modal HTMX
# ---------------------------------------------------------------------------

@role_required(UserRole.GESTOR)
def politica_rules_modal(request, pk: int):
    policy = get_object_or_404(SitePolicy, pk=pk)
    busca = request.GET.get("q", "").strip()
    rules_qs = policy.rules.all().order_by("domain")
    if busca:
        rules_qs = rules_qs.filter(domain__icontains=busca)

    active_cats = set(policy.active_categories())
    categorias = []
    for key, cat in SITE_CATEGORIES.items():
        categorias.append({
            "key": key,
            "label": cat["label"],
            "count": len(cat["domains"]),
            "active": key in active_cats,
        })

    return render(request, "agentes/site_policies/_rules_modal.html", {
        "p": policy,
        "rules": rules_qs,
        "busca": busca,
        "categorias": categorias,
    })


@role_required(UserRole.GESTOR)
@require_POST
def politica_toggle_categoria(request, pk: int, slug: str):
    policy = get_object_or_404(SitePolicy, pk=pk)
    if slug not in SITE_CATEGORIES:
        return HttpResponseBadRequest("Categoria inválida")
    if slug in policy.active_categories():
        policy.remove_category(slug)
    else:
        policy.add_category(slug)
    policy.save(update_fields=["updated_at"])
    _enqueue_apply_for_policy(policy, request.user)
    return _htmx_redirect_rules(request, policy)


@role_required(UserRole.GESTOR)
@require_POST
def politica_add_regra(request, pk: int):
    policy = get_object_or_404(SitePolicy, pk=pk)
    domain = _normalize_domain(request.POST.get("domain", ""))
    action = request.POST.get("action", "block")
    if action not in {"block", "allow"}:
        action = "block"
    if not domain:
        messages.error(request, "Domínio inválido.")
        return _htmx_redirect_rules(request, policy)
    SiteRule.objects.update_or_create(
        site_policy=policy,
        domain=domain,
        defaults={"action": action, "category": ""},
    )
    policy.save(update_fields=["updated_at"])
    _enqueue_apply_for_policy(policy, request.user)
    return _htmx_redirect_rules(request, policy)


@role_required(UserRole.GESTOR)
@require_POST
def politica_del_regra(request, pk: int, regra_pk: int):
    policy = get_object_or_404(SitePolicy, pk=pk)
    SiteRule.objects.filter(pk=regra_pk, site_policy=policy).delete()
    policy.save(update_fields=["updated_at"])
    _enqueue_apply_for_policy(policy, request.user)
    return _htmx_redirect_rules(request, policy)


def _htmx_redirect_rules(request, policy: SitePolicy):
    """Reabre o modal de regras (HTMX swap) após cada mutação."""
    return politica_rules_modal(request, policy.pk)


# ---------------------------------------------------------------------------
# Atribuição a workstations (agent tokens) — modal HTMX
# ---------------------------------------------------------------------------

@role_required(UserRole.GESTOR)
def politica_assign_modal(request, pk: int):
    policy = get_object_or_404(SitePolicy, pk=pk)
    agents = (
        AgentToken.objects.filter(active=True)
        .order_by("hostname", "name")
    )
    assigned_ids = set(
        WorkstationPolicy.objects.filter(site_policy=policy).values_list(
            "agent_token_id", flat=True
        )
    )
    return render(request, "agentes/site_policies/_assign_modal.html", {
        "p": policy,
        "agents": agents,
        "assigned_ids": assigned_ids,
    })


@role_required(UserRole.GESTOR)
@require_POST
def politica_toggle_alvo(request, pk: int, agent_pk: int):
    policy = get_object_or_404(SitePolicy, pk=pk)
    agent = get_object_or_404(AgentToken, pk=agent_pk)
    existing = WorkstationPolicy.objects.filter(
        site_policy=policy, agent_token=agent
    ).first()
    if existing:
        existing.delete()
    else:
        WorkstationPolicy.objects.create(site_policy=policy, agent_token=agent)
    _enqueue_apply_policies([agent.id], created_by=request.user)
    return politica_assign_modal(request, policy.pk)


# ---------------------------------------------------------------------------
# Sites Bloqueados — lista simples por tenant
# ---------------------------------------------------------------------------

@role_required(UserRole.GESTOR)
def sites_bloqueados(request):
    sites = BlockedSite.objects.select_related("created_by").order_by("-created_at")
    total = sites.count()
    ativos = sites.filter(active=True).count()
    inativos = total - ativos
    return render(request, "agentes/sites_bloqueados/list.html", {
        "sites": sites,
        "total": total,
        "ativos": ativos,
        "inativos": inativos,
    })


@role_required(UserRole.GESTOR)
@require_POST
def sites_bloqueados_save(request):
    pk = request.POST.get("id") or None
    domain = _normalize_domain(request.POST.get("domain", ""))
    reason = (request.POST.get("reason") or "").strip()[:500]
    if not domain:
        messages.error(request, "Domínio é obrigatório.")
        return redirect("agentes:sites_bloqueados")
    if pk:
        site = get_object_or_404(BlockedSite, pk=pk)
        site.domain = domain[:255]
        site.reason = reason
        site.save(update_fields=["domain", "reason", "updated_at"])
        messages.success(request, "Site atualizado.")
    else:
        BlockedSite.objects.update_or_create(
            domain=domain[:255],
            defaults={
                "reason": reason,
                "active": True,
                "created_by": request.user,
            },
        )
        messages.success(request, f'Site "{domain}" bloqueado.')
    return redirect("agentes:sites_bloqueados")


@role_required(UserRole.GESTOR)
@require_POST
def sites_bloqueados_toggle(request, pk: int):
    site = get_object_or_404(BlockedSite, pk=pk)
    site.active = not site.active
    site.save(update_fields=["active", "updated_at"])
    return redirect("agentes:sites_bloqueados")


@role_required(UserRole.GESTOR)
@require_POST
def sites_bloqueados_delete(request, pk: int):
    site = get_object_or_404(BlockedSite, pk=pk)
    domain = site.domain
    site.delete()
    messages.success(request, f'"{domain}" removido.')
    return redirect("agentes:sites_bloqueados")
