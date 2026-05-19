"""Views do módulo Transporte — porte do painel Laravel."""
from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .forms import (
    CidadeDestinoForm,
    HorarioTransporteForm,
    LocalAtendimentoForm,
    LocalEmbarqueForm,
    MotoristaForm,
    PacienteForm,
    PassageiroViagemForm,
    ProtocoloExameForm,
    ViagemTransporteForm,
)
from .models import (
    CidadeDestino,
    HorarioTransporte,
    LocalAtendimento,
    LocalEmbarque,
    Motorista,
    Paciente,
    PassageiroViagem,
    ProtocoloExame,
    ViagemTransporte,
)


# ─────────────────────────── helpers ───────────────────────────


def _modal_ctx(model, form_class, request, search_fields=()):
    """Constrói contexto comum p/ listas com modal CRUD."""
    search = (request.GET.get("q") or "").strip()
    qs = model.objects.order_by(*(model._meta.ordering or ["pk"]))
    if search and search_fields:
        cond = Q()
        for f in search_fields:
            cond |= Q(**{f"{f}__icontains": search})
        qs = qs.filter(cond)
    editing = None
    edit_pk = request.GET.get("editar")
    if edit_pk:
        editing = get_object_or_404(model, pk=edit_pk)
    show_modal = request.GET.get("novo") == "1" or bool(editing)
    form = form_class(instance=editing) if show_modal else None
    return {
        "items": qs,
        "search": search,
        "form": form,
        "editing": editing,
        "show_modal": show_modal,
    }


# ─────────────────────────── Cidades ───────────────────────────


@login_required
def cidade_list(request):
    return render(request, "transporte/cidade_list.html",
                  _modal_ctx(CidadeDestino, CidadeDestinoForm, request, ("nome", "uf")))


@login_required
@require_POST
def cidade_save(request, pk: int | None = None):
    instance = get_object_or_404(CidadeDestino, pk=pk) if pk else CidadeDestino()
    form = CidadeDestinoForm(request.POST, instance=instance)
    if form.is_valid():
        form.save()
        messages.success(request, f"Cidade {'atualizada' if pk else 'cadastrada'}.")
        return redirect("transporte:cidade_list")
    ctx = _modal_ctx(CidadeDestino, CidadeDestinoForm, request, ("nome", "uf"))
    ctx.update({"form": form, "show_modal": True, "editing": instance if pk else None})
    return render(request, "transporte/cidade_list.html", ctx, status=422)


@login_required
@require_POST
def cidade_delete(request, pk: int):
    c = get_object_or_404(CidadeDestino, pk=pk)
    if c.locais_atendimento.exists():
        messages.error(request, "Esta cidade tem locais de atendimento vinculados.")
    else:
        c.delete()
        messages.success(request, "Cidade excluída.")
    return redirect("transporte:cidade_list")


@login_required
@require_POST
def cidade_toggle(request, pk: int):
    c = get_object_or_404(CidadeDestino, pk=pk)
    c.ativo = not c.ativo
    c.save(update_fields=["ativo"])
    return redirect("transporte:cidade_list")


# ─────────────────────────── Locais de atendimento ───────────────────────────


@login_required
def local_atendimento_list(request):
    return render(request, "transporte/local_atendimento_list.html",
                  _modal_ctx(LocalAtendimento, LocalAtendimentoForm, request, ("nome", "endereco")))


@login_required
@require_POST
def local_atendimento_save(request, pk: int | None = None):
    instance = get_object_or_404(LocalAtendimento, pk=pk) if pk else LocalAtendimento()
    form = LocalAtendimentoForm(request.POST, instance=instance)
    if form.is_valid():
        form.save()
        messages.success(request, f"Local de atendimento {'atualizado' if pk else 'cadastrado'}.")
        return redirect("transporte:local_atendimento_list")
    ctx = _modal_ctx(LocalAtendimento, LocalAtendimentoForm, request, ("nome", "endereco"))
    ctx.update({"form": form, "show_modal": True, "editing": instance if pk else None})
    return render(request, "transporte/local_atendimento_list.html", ctx, status=422)


@login_required
@require_POST
def local_atendimento_delete(request, pk: int):
    l = get_object_or_404(LocalAtendimento, pk=pk)
    l.delete()
    messages.success(request, "Local excluído.")
    return redirect("transporte:local_atendimento_list")


# ─────────────────────────── Locais de embarque ───────────────────────────


@login_required
def local_embarque_list(request):
    return render(request, "transporte/local_embarque_list.html",
                  _modal_ctx(LocalEmbarque, LocalEmbarqueForm, request, ("nome", "endereco")))


@login_required
@require_POST
def local_embarque_save(request, pk: int | None = None):
    instance = get_object_or_404(LocalEmbarque, pk=pk) if pk else LocalEmbarque()
    form = LocalEmbarqueForm(request.POST, instance=instance)
    if form.is_valid():
        form.save()
        messages.success(request, f"Local de embarque {'atualizado' if pk else 'cadastrado'}.")
        return redirect("transporte:local_embarque_list")
    ctx = _modal_ctx(LocalEmbarque, LocalEmbarqueForm, request, ("nome", "endereco"))
    ctx.update({"form": form, "show_modal": True, "editing": instance if pk else None})
    return render(request, "transporte/local_embarque_list.html", ctx, status=422)


@login_required
@require_POST
def local_embarque_delete(request, pk: int):
    l = get_object_or_404(LocalEmbarque, pk=pk)
    l.delete()
    messages.success(request, "Local excluído.")
    return redirect("transporte:local_embarque_list")


# ─────────────────────────── Horários ───────────────────────────


@login_required
def horario_list(request):
    return render(request, "transporte/horario_list.html",
                  _modal_ctx(HorarioTransporte, HorarioTransporteForm, request, ("descricao",)))


@login_required
@require_POST
def horario_save(request, pk: int | None = None):
    instance = get_object_or_404(HorarioTransporte, pk=pk) if pk else HorarioTransporte()
    form = HorarioTransporteForm(request.POST, instance=instance)
    if form.is_valid():
        form.save()
        messages.success(request, f"Horário {'atualizado' if pk else 'cadastrado'}.")
        return redirect("transporte:horario_list")
    ctx = _modal_ctx(HorarioTransporte, HorarioTransporteForm, request, ("descricao",))
    ctx.update({"form": form, "show_modal": True, "editing": instance if pk else None})
    return render(request, "transporte/horario_list.html", ctx, status=422)


@login_required
@require_POST
def horario_delete(request, pk: int):
    h = get_object_or_404(HorarioTransporte, pk=pk)
    h.delete()
    messages.success(request, "Horário excluído.")
    return redirect("transporte:horario_list")


# ─────────────────────────── Motoristas ───────────────────────────


@login_required
def motorista_list(request):
    search = (request.GET.get("q") or "").strip()
    filtro_cnh = (request.GET.get("cnh") or "todos").strip()
    qs = Motorista.objects.select_related("user").order_by("nome")
    if search:
        qs = qs.filter(Q(nome__icontains=search) | Q(cnh__icontains=search))
    hoje = timezone.localdate()
    if filtro_cnh == "valida":
        qs = qs.filter(cnh_validade__gt=hoje + timedelta(days=30))
    elif filtro_cnh == "a_vencer":
        qs = qs.filter(cnh_validade__gte=hoje, cnh_validade__lte=hoje + timedelta(days=30))
    elif filtro_cnh == "vencida":
        qs = qs.filter(cnh_validade__lt=hoje)

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))

    editing = None
    edit_pk = request.GET.get("editar")
    if edit_pk:
        editing = get_object_or_404(Motorista, pk=edit_pk)
    show_modal = request.GET.get("novo") == "1" or bool(editing)
    form = MotoristaForm(instance=editing) if show_modal else None

    alertas = {
        "vencidas": Motorista.objects.filter(ativo=True, cnh_validade__lt=hoje).count(),
        "a_vencer": Motorista.objects.filter(
            ativo=True, cnh_validade__gte=hoje, cnh_validade__lte=hoje + timedelta(days=30)
        ).count(),
    }

    return render(request, "transporte/motorista_list.html", {
        "page": page, "motoristas": page.object_list,
        "search": search, "filtro_cnh": filtro_cnh, "alertas": alertas,
        "form": form, "editing": editing, "show_modal": show_modal,
        "hoje": hoje, "limite_avenc": hoje + timedelta(days=30),
    })


@login_required
@require_POST
def motorista_save(request, pk: int | None = None):
    instance = get_object_or_404(Motorista, pk=pk) if pk else Motorista()
    form = MotoristaForm(request.POST, instance=instance)
    if form.is_valid():
        m = form.save()
        messages.success(request, f"Motorista {m.nome} {'atualizado' if pk else 'cadastrado'}.")
        return redirect("transporte:motorista_list")
    return motorista_list(request)


@login_required
@require_POST
def motorista_delete(request, pk: int):
    m = get_object_or_404(Motorista, pk=pk)
    if m.viagens_transporte.exists():
        messages.error(request, "Motorista possui viagens vinculadas.")
    else:
        m.delete()
        messages.success(request, "Motorista excluído.")
    return redirect("transporte:motorista_list")


# ─────────────────────────── Pacientes ───────────────────────────


@login_required
def paciente_list(request):
    search = (request.GET.get("q") or "").strip()
    unidade = (request.GET.get("unidade") or "").strip()

    qs = Paciente.objects.order_by("nome")
    if search:
        qs = qs.filter(
            Q(nome__icontains=search)
            | Q(cpf__icontains=search)
            | Q(cns__icontains=search)
            | Q(telefone__icontains=search)
        )
    if unidade:
        qs = qs.filter(unidade__icontains=unidade)

    paginator = Paginator(qs, 25)
    page = paginator.get_page(request.GET.get("page"))

    editing = None
    edit_pk = request.GET.get("editar")
    if edit_pk:
        editing = get_object_or_404(Paciente, pk=edit_pk)
    show_modal = request.GET.get("novo") == "1" or bool(editing)
    form = PacienteForm(instance=editing) if show_modal else None

    unidades = list(
        Paciente.objects.exclude(unidade="").values_list("unidade", flat=True).distinct().order_by("unidade")
    )

    return render(request, "transporte/paciente_list.html", {
        "page": page, "pacientes": page.object_list,
        "search": search, "unidade": unidade, "unidades": unidades,
        "form": form, "editing": editing, "show_modal": show_modal,
    })


@login_required
@require_POST
def paciente_save(request, pk: int | None = None):
    instance = get_object_or_404(Paciente, pk=pk) if pk else Paciente()
    form = PacienteForm(request.POST, instance=instance)
    if form.is_valid():
        p = form.save()
        messages.success(request, f"Paciente {p.nome} {'atualizado' if pk else 'cadastrado'}.")
        return redirect("transporte:paciente_list")
    return paciente_list(request)


@login_required
@require_POST
def paciente_delete(request, pk: int):
    p = get_object_or_404(Paciente, pk=pk)
    if p.passageiro_viagens.exists() or p.protocolos_exame.exists():
        messages.error(request, "Paciente tem viagens ou protocolos vinculados.")
    else:
        p.delete()
        messages.success(request, "Paciente excluído.")
    return redirect("transporte:paciente_list")


# ─────────────────────────── Protocolos ───────────────────────────


@login_required
def protocolo_list(request):
    search = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    tipo = (request.GET.get("tipo") or "").strip()

    qs = ProtocoloExame.objects.select_related("paciente", "local_atendimento", "viagem_origem").order_by("-created_at")
    if search:
        qs = qs.filter(
            Q(paciente__nome__icontains=search)
            | Q(descricao__icontains=search)
            | Q(numero_protocolo__icontains=search)
        )
    if status:
        qs = qs.filter(status=status)
    if tipo:
        qs = qs.filter(tipo=tipo)

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "transporte/protocolo_list.html", {
        "page": page, "protocolos": page.object_list,
        "search": search, "status_filter": status, "tipo_filter": tipo,
        "status_choices": ProtocoloExame.STATUS_CHOICES,
        "tipo_choices": ProtocoloExame.TIPO_CHOICES,
    })


@login_required
@require_http_methods(["GET", "POST"])
def protocolo_create(request):
    if request.method == "POST":
        form = ProtocoloExameForm(request.POST)
        if form.is_valid():
            p = form.save(commit=False)
            p.criado_por = request.user
            p.save()
            messages.success(request, "Protocolo cadastrado.")
            return redirect("transporte:protocolo_list")
    else:
        form = ProtocoloExameForm()
    return render(request, "transporte/protocolo_form.html", {"form": form, "editing": None})


@login_required
@require_http_methods(["GET", "POST"])
def protocolo_edit(request, pk: int):
    p = get_object_or_404(ProtocoloExame, pk=pk)
    if request.method == "POST":
        form = ProtocoloExameForm(request.POST, instance=p)
        if form.is_valid():
            form.save()
            messages.success(request, "Protocolo atualizado.")
            return redirect("transporte:protocolo_list")
    else:
        form = ProtocoloExameForm(instance=p)
    return render(request, "transporte/protocolo_form.html", {"form": form, "editing": p})


@login_required
@require_POST
def protocolo_marcar_retirado(request, pk: int):
    p = get_object_or_404(ProtocoloExame, pk=pk)
    p.status = "aguardando_entrega"
    p.retirado_em = timezone.now()
    p.retirado_por = request.user
    p.save()
    messages.success(request, f"Protocolo '{p.descricao}' marcado como retirado.")
    return redirect("transporte:protocolo_list")


@login_required
@require_POST
def protocolo_marcar_entregue(request, pk: int):
    p = get_object_or_404(ProtocoloExame, pk=pk)
    p.status = "entregue"
    p.entregue_em = timezone.now()
    p.entregue_por = request.user
    p.entregue_para = request.POST.get("entregue_para", "") or ""
    p.save()
    messages.success(request, f"Protocolo '{p.descricao}' marcado como entregue.")
    return redirect("transporte:protocolo_list")


# ─────────────────────────── Viagens ───────────────────────────


@login_required
def viagem_list(request):
    search = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    data_inicio = (request.GET.get("data_inicio") or "").strip()
    data_fim = (request.GET.get("data_fim") or "").strip()

    qs = (
        ViagemTransporte.objects
        .select_related("veiculo", "motorista", "cidade_destino", "horario")
        .order_by("-data", "-hora_saida")
    )
    if search:
        qs = qs.filter(
            Q(motorista__nome__icontains=search)
            | Q(veiculo__placa__icontains=search)
            | Q(cidade_destino__nome__icontains=search)
        )
    if status:
        qs = qs.filter(status=status)
    if data_inicio:
        qs = qs.filter(data__gte=data_inicio)
    if data_fim:
        qs = qs.filter(data__lte=data_fim)

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "transporte/viagem_list.html", {
        "page": page, "viagens": page.object_list,
        "search": search, "status_filter": status,
        "data_inicio": data_inicio, "data_fim": data_fim,
        "status_choices": ViagemTransporte.STATUS_CHOICES,
    })


@login_required
@require_http_methods(["GET", "POST"])
def viagem_create(request):
    if request.method == "POST":
        form = ViagemTransporteForm(request.POST)
        if form.is_valid():
            v = form.save(commit=False)
            v.criado_por = request.user
            v.save()
            messages.success(request, f"Viagem #{v.pk} criada. Adicione passageiros.")
            return redirect("transporte:viagem_detail", pk=v.pk)
    else:
        form = ViagemTransporteForm(initial={"data": timezone.localdate()})
    return render(request, "transporte/viagem_form.html", {"form": form, "editing": None})


@login_required
@require_http_methods(["GET", "POST"])
def viagem_edit(request, pk: int):
    v = get_object_or_404(ViagemTransporte, pk=pk)
    if request.method == "POST":
        form = ViagemTransporteForm(request.POST, instance=v)
        if form.is_valid():
            form.save()
            messages.success(request, f"Viagem #{v.pk} atualizada.")
            return redirect("transporte:viagem_detail", pk=v.pk)
    else:
        form = ViagemTransporteForm(instance=v)
    return render(request, "transporte/viagem_form.html", {"form": form, "editing": v})


@login_required
def viagem_detail(request, pk: int):
    v = get_object_or_404(
        ViagemTransporte.objects.select_related("veiculo", "motorista", "cidade_destino", "horario", "criado_por"),
        pk=pk,
    )
    passageiros = (
        PassageiroViagem.objects
        .filter(viagem=v)
        .select_related("paciente", "acompanhante", "local_atendimento", "local_embarque")
        .order_by("id")
    )
    passageiro_form = PassageiroViagemForm()
    return render(request, "transporte/viagem_detail.html", {
        "v": v, "passageiros": passageiros, "passageiro_form": passageiro_form,
    })


@login_required
@require_POST
def viagem_add_passageiro(request, pk: int):
    v = get_object_or_404(ViagemTransporte, pk=pk)
    form = PassageiroViagemForm(request.POST)
    if form.is_valid():
        passageiro = form.save(commit=False)
        passageiro.viagem = v
        try:
            passageiro.save()
            messages.success(request, f"Passageiro {passageiro.paciente.nome} adicionado.")
        except Exception:
            messages.error(request, "Esse paciente já está na lista.")
    else:
        messages.error(request, "Erro ao adicionar passageiro.")
    return redirect("transporte:viagem_detail", pk=v.pk)


@login_required
@require_POST
def viagem_remove_passageiro(request, pk: int, passageiro_pk: int):
    p = get_object_or_404(PassageiroViagem, pk=passageiro_pk, viagem_id=pk)
    nome = p.paciente.nome
    p.delete()
    messages.success(request, f"{nome} removido da viagem.")
    return redirect("transporte:viagem_detail", pk=pk)


@login_required
@require_POST
def viagem_status(request, pk: int):
    v = get_object_or_404(ViagemTransporte, pk=pk)
    novo = request.POST.get("status")
    if novo in dict(ViagemTransporte.STATUS_CHOICES):
        v.status = novo
        v.save(update_fields=["status"])
        messages.success(request, f"Status alterado para {v.get_status_display()}.")
    return redirect("transporte:viagem_detail", pk=v.pk)
