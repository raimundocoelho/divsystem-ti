"""Views do módulo Frota.

Espelha o painel Laravel (componentes Livewire em resources/views/components/frota/*).
Todas as queries usam `Veiculo.objects` / `DiarioBordo.objects` que filtram
automaticamente pelo tenant ativo (ver apps.core.models.TenantOwnedModel).
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.organizacoes.models import Secretaria

from .forms import DiarioBordoForm, RelatorioFrotaFiltroForm, VeiculoForm
from .models import DiarioBordo, Veiculo


# ─────────────────────────── Veículos ───────────────────────────


@login_required
def veiculo_list(request):
    search = (request.GET.get("q") or "").strip()
    qs = Veiculo.objects.select_related("secretaria").order_by("placa")
    if search:
        qs = qs.filter(
            Q(placa__icontains=search)
            | Q(modelo__icontains=search)
            | Q(nome__icontains=search)
        )
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get("page"))

    editing = None
    edit_pk = request.GET.get("editar")
    if edit_pk:
        editing = get_object_or_404(Veiculo, pk=edit_pk)

    show_modal = request.GET.get("novo") == "1" or bool(editing)
    form = VeiculoForm(instance=editing) if show_modal else None

    return render(
        request,
        "frota/veiculo_list.html",
        {
            "page": page,
            "veiculos": page.object_list,
            "search": search,
            "secretarias": Secretaria.objects.filter(ativo=True).order_by("nome"),
            "form": form,
            "editing": editing,
            "show_modal": show_modal,
        },
    )


@login_required
@require_POST
def veiculo_save(request, pk: int | None = None):
    instance = get_object_or_404(Veiculo, pk=pk) if pk else Veiculo()
    form = VeiculoForm(request.POST, instance=instance)
    if form.is_valid():
        veiculo = form.save()
        messages.success(
            request,
            f"Veículo {veiculo.placa} {'atualizado' if pk else 'cadastrado'}.",
        )
        return redirect("frota:veiculo_list")

    qs = Veiculo.objects.select_related("secretaria").order_by("placa")
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "frota/veiculo_list.html",
        {
            "page": page,
            "veiculos": page.object_list,
            "search": "",
            "secretarias": Secretaria.objects.filter(ativo=True).order_by("nome"),
            "form": form,
            "editing": instance if pk else None,
            "show_modal": True,
        },
        status=422,
    )


# ─────────────────────────── Diários de Bordo ───────────────────────────


def _filtros_diario(request):
    return {
        "search": (request.GET.get("q") or "").strip(),
        "status": (request.GET.get("status") or "").strip(),
        "data_inicio": (request.GET.get("data_inicio") or "").strip(),
        "data_fim": (request.GET.get("data_fim") or "").strip(),
        "veiculo": (request.GET.get("veiculo") or "").strip(),
    }


@login_required
def diario_list(request):
    f = _filtros_diario(request)
    qs = (
        DiarioBordo.objects
        .select_related("veiculo", "condutor", "viagem_transporte")
        .order_by("-saida_em", "-id")
    )

    if f["search"]:
        qs = qs.filter(
            Q(veiculo__placa__icontains=f["search"])
            | Q(veiculo__modelo__icontains=f["search"])
            | Q(condutor__name__icontains=f["search"])
        )
    if f["status"] == "andamento":
        qs = qs.filter(retorno_em__isnull=True)
    elif f["status"] == "concluida":
        qs = qs.filter(retorno_em__isnull=False)
    if f["veiculo"]:
        qs = qs.filter(veiculo_id=f["veiculo"])
    if f["data_inicio"]:
        qs = qs.filter(saida_em__date__gte=f["data_inicio"])
    if f["data_fim"]:
        qs = qs.filter(saida_em__date__lte=f["data_fim"])

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "frota/diario_list.html",
        {
            "page": page,
            "diarios": page.object_list,
            "veiculos": Veiculo.objects.order_by("placa"),
            "filtros": f,
            "tem_filtro": any(f.values()),
        },
    )


def _last_km_retorno(veiculo_id: int, exclude_pk: int | None = None) -> int | None:
    qs = (
        DiarioBordo.objects
        .filter(veiculo_id=veiculo_id, retorno_em__isnull=False, km_retorno__isnull=False)
        .order_by("-retorno_em", "-id")
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    last = qs.first()
    return last.km_retorno if last else None


@login_required
@require_http_methods(["GET", "POST"])
def diario_create(request):
    if request.method == "POST":
        form = DiarioBordoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Viagem registrada com sucesso.")
            return redirect("frota:diario_list")
    else:
        form = DiarioBordoForm()

    return render(
        request,
        "frota/diario_form.html",
        {
            "form": form,
            "veiculos": Veiculo.objects.select_related("secretaria").order_by("placa"),
            "diario": None,
            "ja_fechada": False,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def diario_edit(request, pk: int):
    diario = get_object_or_404(DiarioBordo, pk=pk)
    if request.method == "POST":
        form = DiarioBordoForm(request.POST, instance=diario)
        if form.is_valid():
            form.save()
            messages.success(request, "Viagem atualizada com sucesso.")
            return redirect("frota:diario_list")
    else:
        form = DiarioBordoForm(instance=diario)

    return render(
        request,
        "frota/diario_form.html",
        {
            "form": form,
            "veiculos": Veiculo.objects.select_related("secretaria").order_by("placa"),
            "diario": diario,
            "ja_fechada": diario.retorno_em is not None,
        },
    )


@login_required
def diario_last_km(request):
    """AJAX: retorna o KM de retorno da última viagem concluída do veículo."""
    veiculo_id = request.GET.get("veiculo")
    exclude = request.GET.get("exclude") or None
    if not veiculo_id:
        return HttpResponse("", content_type="text/plain")
    km = _last_km_retorno(int(veiculo_id), int(exclude) if exclude else None)
    return HttpResponse(str(km) if km is not None else "", content_type="text/plain")


# ─────────────────────────── Relatórios ───────────────────────────


@login_required
@require_http_methods(["GET", "POST"])
def relatorios(request):
    hoje = timezone.localdate()
    primeiro = hoje.replace(day=1)
    ultimo = (primeiro + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    inicial = {"data_inicio": primeiro, "data_fim": ultimo}

    if request.method == "POST":
        form = RelatorioFrotaFiltroForm(request.POST)
        if form.is_valid():
            return _gerar_pdf_km(request, form)
    else:
        form = RelatorioFrotaFiltroForm(initial=inicial)

    return render(request, "frota/relatorios.html", {"form": form})


def _gerar_pdf_km(request, form: RelatorioFrotaFiltroForm) -> HttpResponse:
    data_inicio = form.cleaned_data.get("data_inicio")
    data_fim = form.cleaned_data.get("data_fim")
    secretaria = form.cleaned_data.get("secretaria")
    veiculo = form.cleaned_data.get("veiculo")

    from django.db.models import F, ExpressionWrapper, IntegerField
    qs = (
        DiarioBordo.objects
        .select_related("veiculo", "veiculo__secretaria", "condutor", "autorizador")
        .annotate(km_rodados=ExpressionWrapper(F("km_retorno") - F("km_saida"), output_field=IntegerField()))
        .order_by("saida_em")
    )
    if data_inicio:
        qs = qs.filter(saida_em__date__gte=data_inicio)
    if data_fim:
        qs = qs.filter(saida_em__date__lte=data_fim)
    if secretaria:
        qs = qs.filter(veiculo__secretaria_id=secretaria.pk)
    if veiculo:
        qs = qs.filter(veiculo_id=veiculo.pk)

    diarios = list(qs)
    total_km = sum(
        (d.km_retorno - d.km_saida)
        for d in diarios
        if d.km_retorno is not None and d.km_saida is not None
    )

    html = render(
        request,
        "frota/relatorio_km_pdf.html",
        {
            "diarios": diarios,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "secretaria": secretaria,
            "veiculo": veiculo,
            "total_km": total_km,
            "gerado_em": timezone.now(),
        },
    ).content.decode("utf-8")

    try:
        from weasyprint import HTML  # type: ignore
        pdf_bytes = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
        resp = HttpResponse(pdf_bytes, content_type="application/pdf")
        nome = f"relatorio-frota-{data_inicio or 'inicio'}-{data_fim or 'fim'}.pdf"
        resp["Content-Disposition"] = f'inline; filename="{nome}"'
        return resp
    except ImportError:
        return HttpResponse(html)
