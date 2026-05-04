"""Views do módulo Mikrotik.

Tudo escopado pelo tenant ativo (resolvido por ResolveTenantMiddleware).
"""
from __future__ import annotations

import secrets
from http import HTTPStatus

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods, require_POST

from apps.mikrotik.forms import DeviceForm, EnviarComandoForm, EquipamentoForm
from apps.mikrotik.models import Comando, Device, Equipamento, RogueAlert
from apps.mikrotik.services import api as api_svc
from apps.mikrotik.services import devices as devices_svc
from apps.mikrotik.services import provisioning, wireguard


def _generate_api_password() -> str:
    return secrets.token_urlsafe(24)


@login_required
def equipamento_list(request):
    equipamentos = Equipamento.objects.select_related("secretaria", "setor").order_by("nome")
    return render(request, "mikrotik/equipamento_list.html", {"equipamentos": equipamentos})


@login_required
@require_http_methods(["GET", "POST"])
def equipamento_create(request):
    if request.method == "POST":
        form = EquipamentoForm(request.POST)
        if form.is_valid():
            eq: Equipamento = form.save(commit=False)
            eq.criado_por = request.user
            eq.api_password = _generate_api_password()
            eq.save()
            messages.success(request, "Equipamento cadastrado. Provisione-o para gerar o script de bootstrap.")
            return redirect("mikrotik:detail", slug=eq.slug)
    else:
        form = EquipamentoForm()
    return render(request, "mikrotik/equipamento_form.html", {"form": form})


@login_required
def equipamento_detail(request, slug):
    eq = get_object_or_404(Equipamento, slug=slug)
    comandos = eq.comandos.all()[:20]
    cmd_form = EnviarComandoForm()
    return render(
        request,
        "mikrotik/equipamento_detail.html",
        {"eq": eq, "comandos": comandos, "cmd_form": cmd_form},
    )


@login_required
@require_POST
def equipamento_provisionar(request, slug):
    eq = get_object_or_404(Equipamento, slug=slug)
    try:
        wireguard.provision_equipamento(eq)
        messages.success(request, f"Peer WG cadastrado em 10.10.10.0/24 — IP: {eq.wg_ip}")
    except wireguard.WireGuardError as exc:
        messages.error(request, f"Falha no provisionamento: {exc}")
    return redirect("mikrotik:detail", slug=eq.slug)


@login_required
def equipamento_script(request, slug):
    """Retorna o script .rsc de bootstrap para download."""
    from django.conf import settings as dj_settings

    eq = get_object_or_404(Equipamento, slug=slug)
    if not eq.wg_ip or not eq.wg_privkey_device:
        messages.error(request, "Provisione o equipamento antes de gerar o script.")
        return redirect("mikrotik:detail", slug=eq.slug)

    nova_senha = request.GET.get("admin_password") or eq.api_password
    script = provisioning.gerar_script_bootstrap(
        eq,
        server_pubkey=getattr(dj_settings, "WG_SERVER_PUBKEY", ""),
        server_endpoint_host=getattr(dj_settings, "WG_ENDPOINT_HOST", "178.105.4.179"),
        server_endpoint_port=int(getattr(dj_settings, "WG_ENDPOINT_PORT", 51820)),
        nova_senha_admin=nova_senha,
    )
    response = HttpResponse(script, content_type="text/plain; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="bootstrap-{eq.slug}.rsc"'
    return response


@login_required
@require_POST
def equipamento_enviar_comando(request, slug):
    eq = get_object_or_404(Equipamento, slug=slug)
    form = EnviarComandoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Dados do comando inválidos.")
        return redirect("mikrotik:detail", slug=eq.slug)

    cmd = Comando.objects.create(
        equipamento=eq,
        tipo=form.cleaned_data["tipo"],
        path=form.cleaned_data["path"],
        payload=form.cleaned_data["payload"],
        executado_por=request.user,
    )
    api_svc.executar_comando(cmd)
    if cmd.status == "sucesso":
        messages.success(request, f"Comando executado em {cmd.duration_ms} ms.")
    else:
        messages.error(request, f"Falha: {cmd.erro}")
    return redirect("mikrotik:detail", slug=eq.slug)


@login_required
@require_POST
def equipamento_ping(request, slug):
    eq = get_object_or_404(Equipamento, slug=slug)
    try:
        client = api_svc.RouterOSClient(eq)
        ok = client.ping()
        if ok:
            messages.success(request, "Equipamento respondeu (REST /system/identity).")
            eq.status = "online"
            eq.last_error = ""
        else:
            messages.warning(request, "Equipamento não respondeu.")
            eq.status = "offline"
        eq.save(update_fields=["status", "last_error"])
    except api_svc.RouterOSAPIError as exc:
        messages.error(request, f"Erro: {exc}")
        eq.status = "erro"
        eq.last_error = str(exc)[:1000]
        eq.save(update_fields=["status", "last_error"])
    return redirect("mikrotik:detail", slug=eq.slug)


# ===========================================================================
# Devices — admissão de dispositivos
# ===========================================================================


@login_required
def device_list(request, slug):
    eq = get_object_or_404(Equipamento, slug=slug)
    devices = (
        Device.objects.filter(equipamento=eq)
        .select_related("secretaria", "setor")
        .order_by("nome")
    )
    rogue_count = RogueAlert.objects.filter(equipamento=eq, status="novo").count()
    return render(
        request,
        "mikrotik/device_list.html",
        {"eq": eq, "devices": devices, "rogue_count": rogue_count},
    )


@login_required
@require_http_methods(["GET", "POST"])
def device_create(request, slug):
    eq = get_object_or_404(Equipamento, slug=slug)
    initial = {}
    # Quando vier ?mac=xx&ip=yy&hostname=zz (a partir do rogue feed/discovery)
    for k in ("mac", "ip", "hostname", "nome"):
        v = request.GET.get(k)
        if v:
            initial[
                "mac_address" if k == "mac" else "ip_address" if k == "ip" else k
            ] = v

    if request.method == "POST":
        form = DeviceForm(request.POST)
        if form.is_valid():
            device = form.save(commit=False)
            device.equipamento = eq
            device.criado_por = request.user
            device.save()
            # Resolve rogue se houver
            RogueAlert.objects.filter(
                equipamento=eq, mac_address=device.mac_address
            ).update(status="aceito", resolvido_por=request.user)

            # Push pra router se possível
            if device.ip_address and device.status == "ativo":
                try:
                    devices_svc.sync_device_to_router(device)
                    messages.success(
                        request,
                        f"Device cadastrado e static lease criada em {device.ip_address}.",
                    )
                except Exception as exc:  # noqa: BLE001
                    messages.warning(
                        request,
                        f"Device cadastrado, mas falha ao sincronizar com router: {exc}",
                    )
            else:
                messages.success(request, "Device cadastrado.")
            return redirect("mikrotik:device_list", slug=eq.slug)
    else:
        form = DeviceForm(initial=initial)
    return render(
        request,
        "mikrotik/device_form.html",
        {"eq": eq, "form": form, "is_create": True},
    )


@login_required
@require_http_methods(["GET", "POST"])
def device_edit(request, slug, pk):
    eq = get_object_or_404(Equipamento, slug=slug)
    device = get_object_or_404(Device, pk=pk, equipamento=eq)

    if request.method == "POST":
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            device = form.save()
            try:
                devices_svc.sync_device_to_router(device)
                messages.success(request, "Device atualizado e sincronizado.")
            except Exception as exc:  # noqa: BLE001
                messages.warning(request, f"Salvo, mas erro ao sincronizar: {exc}")
            return redirect("mikrotik:device_list", slug=eq.slug)
    else:
        form = DeviceForm(instance=device)
    return render(
        request,
        "mikrotik/device_form.html",
        {"eq": eq, "form": form, "device": device, "is_create": False},
    )


@login_required
@require_POST
def device_sync(request, slug, pk):
    eq = get_object_or_404(Equipamento, slug=slug)
    device = get_object_or_404(Device, pk=pk, equipamento=eq)
    try:
        devices_svc.sync_device_to_router(device)
        messages.success(request, f"Static lease atualizada para {device.nome}.")
    except Exception as exc:  # noqa: BLE001
        messages.error(request, f"Falha ao sincronizar: {exc}")
    return redirect("mikrotik:device_list", slug=eq.slug)


@login_required
@require_POST
def device_delete(request, slug, pk):
    eq = get_object_or_404(Equipamento, slug=slug)
    device = get_object_or_404(Device, pk=pk, equipamento=eq)
    nome = device.nome
    try:
        devices_svc.delete_device_from_router(device)
    except Exception as exc:  # noqa: BLE001
        messages.warning(request, f"Não foi possível remover do router: {exc}")
    device.delete()
    messages.success(request, f"Device '{nome}' removido.")
    return redirect("mikrotik:device_list", slug=eq.slug)


@login_required
@require_POST
def equipamento_discovery(request, slug):
    """Roda discovery imediato e mostra o que foi visto."""
    eq = get_object_or_404(Equipamento, slug=slug)
    try:
        result = devices_svc.pull_observations(eq)
        messages.success(
            request,
            f"Discovery: {len(result.seen)} MAC(s) visto(s), "
            f"{len(result.known)} conhecido(s), "
            f"{len(result.rogues)} desconhecido(s) — "
            f"{result.new_observations} observações registradas.",
        )
    except api_svc.RouterOSAPIError as exc:
        messages.error(request, f"Falha no discovery: {exc}")
    return redirect("mikrotik:device_list", slug=eq.slug)


@login_required
@require_POST
def equipamento_sync_all(request, slug):
    eq = get_object_or_404(Equipamento, slug=slug)
    ok, erros = devices_svc.sync_all_to_router(eq)
    if erros:
        messages.warning(
            request,
            f"{ok} device(s) sincronizados; {len(erros)} falha(s): "
            + "; ".join(erros[:3]),
        )
    else:
        messages.success(request, f"{ok} device(s) sincronizados com o router.")
    return redirect("mikrotik:device_list", slug=eq.slug)


@login_required
def rogue_list(request, slug):
    eq = get_object_or_404(Equipamento, slug=slug)
    rogues = RogueAlert.objects.filter(equipamento=eq).order_by(
        "status", "-ultima_vez"
    )
    return render(
        request,
        "mikrotik/rogue_list.html",
        {"eq": eq, "rogues": rogues},
    )


@login_required
@require_POST
def rogue_action(request, slug, pk):
    """Ações: aceitar (cria Device), bloquear, ignorar."""
    from django.utils import timezone

    eq = get_object_or_404(Equipamento, slug=slug)
    rogue = get_object_or_404(RogueAlert, pk=pk, equipamento=eq)
    action = request.POST.get("action")

    if action == "ignorar":
        rogue.status = "ignorado"
        rogue.resolvido_por = request.user
        rogue.resolvido_em = timezone.now()
        rogue.save()
        messages.success(request, "Alerta marcado como ignorado.")
        return redirect("mikrotik:rogue_list", slug=eq.slug)

    if action == "aceitar":
        # redireciona para criar Device com pré-preenchimento
        params = (
            f"?mac={rogue.mac_address}"
            f"&ip={rogue.primeiro_ip or ''}"
            f"&hostname={rogue.primeiro_hostname}"
            f"&nome={rogue.primeiro_hostname or rogue.mac_address}"
        )
        return redirect(
            reverse("mikrotik:device_create", kwargs={"slug": eq.slug}) + params
        )

    if action == "bloquear":
        rogue.status = "bloqueado"
        rogue.resolvido_por = request.user
        rogue.resolvido_em = timezone.now()
        rogue.save()
        # TODO: empurrar regra de firewall src-mac-address=<mac> action=drop
        messages.success(request, "Alerta marcado como bloqueado (regra de firewall a aplicar).")
        return redirect("mikrotik:rogue_list", slug=eq.slug)

    messages.error(request, f"Ação desconhecida: {action}")
    return redirect("mikrotik:rogue_list", slug=eq.slug)


# ============================================================================
# Políticas de filtro web (DNS sinkhole + firewall TLS-SNI)
# ============================================================================
from apps.mikrotik.forms import PoliticaAlvoForm, PoliticaForm, RegraDominioForm
from apps.mikrotik.models import Politica, PoliticaAlvo, RegraDominio
from apps.mikrotik.services import policies as policies_svc


@login_required
def politica_list(request, slug):
    eq = get_object_or_404(Equipamento, slug=slug)
    politicas = (
        Politica.objects.filter(equipamento=eq)
        .prefetch_related("regras", "alvos")
        .order_by("-created_at")
    )
    return render(request, "mikrotik/politica_list.html", {
        "eq": eq, "politicas": politicas,
    })


@login_required
@require_http_methods(["GET", "POST"])
def politica_create(request, slug):
    eq = get_object_or_404(Equipamento, slug=slug)
    if request.method == "POST":
        form = PoliticaForm(request.POST)
        if form.is_valid():
            p = form.save(commit=False)
            p.equipamento = eq
            p.criado_por = request.user
            p.save()
            messages.success(request, f"Política '{p.nome}' criada. Adicione domínios e alvos abaixo.")
            return redirect("mikrotik:politica_detail", slug=eq.slug, pk=p.pk)
    else:
        form = PoliticaForm()
    return render(request, "mikrotik/politica_form.html", {"eq": eq, "form": form})


@login_required
@require_http_methods(["GET", "POST"])
def politica_detail(request, slug, pk):
    eq = get_object_or_404(Equipamento, slug=slug)
    politica = get_object_or_404(Politica, pk=pk, equipamento=eq)
    regras = politica.regras.all()
    alvos = politica.alvos.select_related("device").all()
    excluir = [a.device_id for a in alvos]

    regra_form = RegraDominioForm()
    alvo_form = PoliticaAlvoForm(equipamento=eq, exclude_devices=excluir)

    return render(request, "mikrotik/politica_detail.html", {
        "eq": eq,
        "politica": politica,
        "regras": regras,
        "alvos": alvos,
        "regra_form": regra_form,
        "alvo_form": alvo_form,
    })


@login_required
@require_POST
def politica_add_dominio(request, slug, pk):
    eq = get_object_or_404(Equipamento, slug=slug)
    politica = get_object_or_404(Politica, pk=pk, equipamento=eq)
    form = RegraDominioForm(request.POST)
    if form.is_valid():
        regra = form.save(commit=False)
        regra.politica = politica
        try:
            regra.save()
            messages.success(request, f"Domínio '{regra.dominio}' adicionado.")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"Falha ao adicionar: {exc}")
    else:
        for err in form.errors.values():
            messages.error(request, "; ".join(err))
    return redirect("mikrotik:politica_detail", slug=eq.slug, pk=politica.pk)


@login_required
@require_POST
def politica_del_dominio(request, slug, pk, regra_pk):
    eq = get_object_or_404(Equipamento, slug=slug)
    politica = get_object_or_404(Politica, pk=pk, equipamento=eq)
    regra = get_object_or_404(RegraDominio, pk=regra_pk, politica=politica)
    nome = regra.dominio
    regra.delete()
    messages.success(request, f"Domínio '{nome}' removido. Aplique a política novamente.")
    return redirect("mikrotik:politica_detail", slug=eq.slug, pk=politica.pk)


@login_required
@require_POST
def politica_add_alvo(request, slug, pk):
    eq = get_object_or_404(Equipamento, slug=slug)
    politica = get_object_or_404(Politica, pk=pk, equipamento=eq)
    form = PoliticaAlvoForm(request.POST, equipamento=eq)
    if form.is_valid():
        device = form.cleaned_data["device"]
        PoliticaAlvo.objects.get_or_create(politica=politica, device=device)
        messages.success(request, f"Device '{device.nome}' adicionado como alvo.")
    else:
        messages.error(request, "Device inválido.")
    return redirect("mikrotik:politica_detail", slug=eq.slug, pk=politica.pk)


@login_required
@require_POST
def politica_del_alvo(request, slug, pk, alvo_pk):
    eq = get_object_or_404(Equipamento, slug=slug)
    politica = get_object_or_404(Politica, pk=pk, equipamento=eq)
    alvo = get_object_or_404(PoliticaAlvo, pk=alvo_pk, politica=politica)
    nome = alvo.device.nome
    alvo.delete()
    messages.success(request, f"Device '{nome}' removido como alvo.")
    return redirect("mikrotik:politica_detail", slug=eq.slug, pk=politica.pk)


@login_required
@require_POST
def politica_aplicar(request, slug, pk):
    eq = get_object_or_404(Equipamento, slug=slug)
    politica = get_object_or_404(Politica, pk=pk, equipamento=eq)
    if not politica.ativo:
        messages.error(request, "Política está inativa — ative antes de aplicar.")
        return redirect("mikrotik:politica_detail", slug=eq.slug, pk=politica.pk)
    try:
        n_dns, n_fw = policies_svc.aplicar_politica(politica)
        messages.success(
            request,
            f"Política aplicada na hEX: {n_dns} entrada(s) DNS + {n_fw} regra(s) firewall.",
        )
    except Exception as exc:  # noqa: BLE001
        messages.error(request, f"Falha ao aplicar: {exc}")
    return redirect("mikrotik:politica_detail", slug=eq.slug, pk=politica.pk)


@login_required
@require_POST
def politica_remover_router(request, slug, pk):
    eq = get_object_or_404(Equipamento, slug=slug)
    politica = get_object_or_404(Politica, pk=pk, equipamento=eq)
    try:
        n_dns, n_fw = policies_svc.remover_politica(politica)
        messages.success(
            request,
            f"Política removida do router: -{n_dns} DNS, -{n_fw} firewall.",
        )
    except Exception as exc:  # noqa: BLE001
        messages.error(request, f"Falha: {exc}")
    return redirect("mikrotik:politica_detail", slug=eq.slug, pk=politica.pk)


@login_required
@require_POST
def politica_delete(request, slug, pk):
    eq = get_object_or_404(Equipamento, slug=slug)
    politica = get_object_or_404(Politica, pk=pk, equipamento=eq)
    nome = politica.nome
    # Tenta remover do router antes de apagar do banco; ignora erro (ex.: hEX off)
    try:
        policies_svc.remover_politica(politica)
    except Exception as exc:  # noqa: BLE001
        messages.warning(request, f"Não removi do router (pode ter sobrado lixo): {exc}")
    politica.delete()
    messages.success(request, f"Política '{nome}' apagada.")
    return redirect("mikrotik:politica_list", slug=eq.slug)


# ============================================================================
# Políticas v2 — tenant-level + modais HTMX (port do painel Laravel antigo)
# ============================================================================
from django.db.models import Count, Q
from apps.mikrotik.services.categorias import (
    CATEGORIAS, listar_categorias, dominios_da_categoria,
)


@login_required
def tenant_politica_list(request):
    """Lista todas as políticas do tenant (todos os equipamentos)."""
    qs = (
        Politica.objects
        .annotate(n_regras=Count("regras", distinct=True), n_alvos=Count("alvos", distinct=True))
        .select_related("equipamento", "criado_por")
        .order_by("-created_at")
    )
    busca = (request.GET.get("q") or "").strip()
    if busca:
        qs = qs.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca))
    politicas = list(qs)

    # Pré-carrega lista de equipamentos pra modal de criação
    equipamentos = Equipamento.objects.order_by("nome")

    return render(request, "mikrotik/politica_tenant_list.html", {
        "politicas": politicas,
        "equipamentos": equipamentos,
        "busca": busca,
    })


@login_required
@require_POST
def tenant_politica_create(request):
    """Cria política via modal (POST direto)."""
    nome = (request.POST.get("nome") or "").strip()
    descricao = (request.POST.get("descricao") or "").strip()
    is_global = bool(request.POST.get("is_global"))
    equipamento_id = request.POST.get("equipamento_id")

    if not nome:
        messages.error(request, "Nome é obrigatório.")
        return redirect("mikrotik:tenant_politica_list")

    eq = get_object_or_404(Equipamento, pk=equipamento_id) if equipamento_id else \
         Equipamento.objects.first()
    if not eq:
        messages.error(request, "Cadastre um equipamento Mikrotik antes.")
        return redirect("mikrotik:tenant_politica_list")

    p = Politica.objects.create(
        tenant=eq.tenant, equipamento=eq,
        nome=nome, descricao=descricao,
        is_global=is_global, ativo=True,
        criado_por=request.user,
    )
    messages.success(request, f"Política '{p.nome}' criada.")
    return redirect("mikrotik:tenant_politica_list")


@login_required
@require_http_methods(["GET", "POST"])
def tenant_politica_edit(request, pk):
    """Edita nome/descrição/is_global via modal."""
    p = get_object_or_404(Politica, pk=pk)
    if request.method == "POST":
        p.nome = (request.POST.get("nome") or p.nome).strip()
        p.descricao = (request.POST.get("descricao") or "").strip()
        p.is_global = bool(request.POST.get("is_global"))
        p.save(update_fields=["nome", "descricao", "is_global", "updated_at"])
        messages.success(request, "Política atualizada.")
        return redirect("mikrotik:tenant_politica_list")
    return render(request, "mikrotik/_politica_edit_modal.html", {"politica": p})


@login_required
@require_POST
def tenant_politica_toggle_active(request, pk):
    p = get_object_or_404(Politica, pk=pk)
    p.ativo = not p.ativo
    p.save(update_fields=["ativo", "updated_at"])
    return redirect("mikrotik:tenant_politica_list")


@login_required
@require_POST
def tenant_politica_aplicar(request, pk):
    p = get_object_or_404(Politica, pk=pk)
    if not p.ativo:
        messages.error(request, "Política está pausada — ative antes de aplicar.")
        return redirect("mikrotik:tenant_politica_list")
    try:
        n_dns, n_fw = policies_svc.aplicar_politica(p)
        messages.success(request, f"Aplicada: {n_dns} entradas DNS + {n_fw} regras firewall.")
    except Exception as exc:  # noqa: BLE001
        messages.error(request, f"Falha: {exc}")
    return redirect("mikrotik:tenant_politica_list")


@login_required
@require_POST
def tenant_politica_remover_router(request, pk):
    p = get_object_or_404(Politica, pk=pk)
    try:
        n_dns, n_fw = policies_svc.remover_politica(p)
        messages.success(request, f"Removida do router: -{n_dns} DNS, -{n_fw} firewall.")
    except Exception as exc:  # noqa: BLE001
        messages.error(request, f"Falha: {exc}")
    return redirect("mikrotik:tenant_politica_list")


@login_required
@require_POST
def tenant_politica_delete(request, pk):
    p = get_object_or_404(Politica, pk=pk)
    nome = p.nome
    try:
        policies_svc.remover_politica(p)
    except Exception as exc:  # noqa: BLE001
        messages.warning(request, f"Pode ter sobrado lixo no router: {exc}")
    p.delete()
    messages.success(request, f"Política '{nome}' apagada.")
    return redirect("mikrotik:tenant_politica_list")


# ---- Modais HTMX: corpo recarregável a cada interação ----
def _render_rules_modal(request, politica):
    cats_ativas = set(politica.categorias_ativas())
    cards = []
    for c in listar_categorias():
        c["ativa"] = c["slug"] in cats_ativas
        cards.append(c)
    busca = (request.GET.get("buscar") or "").strip()
    regras_qs = politica.regras.all().order_by("dominio")
    if busca:
        regras_qs = regras_qs.filter(dominio__icontains=busca)
    return render(request, "mikrotik/_politica_rules_modal.html", {
        "politica": politica,
        "cards": cards,
        "regras": list(regras_qs),
        "total_regras": politica.regras.count(),
        "busca": busca,
        "categorias_labels": {slug: meta["label"] for slug, meta in CATEGORIAS.items()},
    })


@login_required
def tenant_politica_rules_modal(request, pk):
    p = get_object_or_404(Politica, pk=pk)
    return _render_rules_modal(request, p)


@login_required
@require_POST
def tenant_politica_toggle_categoria(request, pk, slug):
    p = get_object_or_404(Politica, pk=pk)
    if slug not in CATEGORIAS:
        return HttpResponse(status=400)
    if slug in p.categorias_ativas():
        p.remove_categoria(slug)
    else:
        p.add_categoria(slug)
    p.save(update_fields=["updated_at"])
    return _render_rules_modal(request, p)


@login_required
@require_POST
def tenant_politica_add_regra_htmx(request, pk):
    from apps.mikrotik.models import RegraDominio
    p = get_object_or_404(Politica, pk=pk)
    dom = (request.POST.get("dominio") or "").strip()
    if dom:
        try:
            RegraDominio.objects.create(politica=p, dominio=dom, categoria="")
        except Exception:  # noqa: BLE001
            pass  # duplicado: ignora silenciosamente
        p.save(update_fields=["updated_at"])
    return _render_rules_modal(request, p)


@login_required
@require_POST
def tenant_politica_del_regra_htmx(request, pk, regra_pk):
    from apps.mikrotik.models import RegraDominio
    p = get_object_or_404(Politica, pk=pk)
    RegraDominio.objects.filter(pk=regra_pk, politica=p).delete()
    p.save(update_fields=["updated_at"])
    return _render_rules_modal(request, p)


# ---- Modal Atribuir ----
def _render_assign_modal(request, politica):
    devices = (
        Device.objects.filter(equipamento=politica.equipamento, status="ativo")
        .order_by("nome")
    )
    alvo_ids = set(politica.alvos.values_list("device_id", flat=True))
    return render(request, "mikrotik/_politica_assign_modal.html", {
        "politica": politica, "devices": devices, "alvo_ids": alvo_ids,
    })


@login_required
def tenant_politica_assign_modal(request, pk):
    p = get_object_or_404(Politica, pk=pk)
    return _render_assign_modal(request, p)


@login_required
@require_POST
def tenant_politica_toggle_alvo_htmx(request, pk, device_pk):
    p = get_object_or_404(Politica, pk=pk)
    device = get_object_or_404(Device, pk=device_pk, equipamento=p.equipamento)
    existing = PoliticaAlvo.objects.filter(politica=p, device=device).first()
    if existing:
        existing.delete()
    else:
        PoliticaAlvo.objects.create(politica=p, device=device)
    p.save(update_fields=["updated_at"])
    return _render_assign_modal(request, p)


# ---- Sites Bloqueados (visão agregada) ----
@login_required
def tenant_sites_bloqueados(request):
    from apps.mikrotik.models import RegraDominio
    # RegraDominio não é TenantOwnedModel — escopa via Politica (que é).
    politicas_do_tenant = Politica.objects.values_list("pk", flat=True)
    qs = (
        RegraDominio.objects.filter(politica__in=politicas_do_tenant)
        .select_related("politica", "politica__equipamento")
        .order_by("dominio")
    )
    busca = (request.GET.get("q") or "").strip()
    cat_filtro = (request.GET.get("cat") or "").strip()
    if busca:
        qs = qs.filter(dominio__icontains=busca)
    if cat_filtro:
        qs = qs.filter(categoria=cat_filtro)
    regras = list(qs[:500])
    total = qs.count()

    return render(request, "mikrotik/sites_bloqueados.html", {
        "regras": regras,
        "total": total,
        "busca": busca,
        "cat_filtro": cat_filtro,
        "categorias": listar_categorias(),
        "categorias_labels": {slug: meta["label"] for slug, meta in CATEGORIAS.items()},
    })
