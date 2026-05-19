"""Views do módulo Patrimônio.

Espelha o painel Laravel (componentes Livewire em resources/views/components/patrimonio/*).
"""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from .forms import PatrimonioCategoriaForm, PatrimonioForm, PatrimonioLocalForm
from .models import (
    Patrimonio,
    PatrimonioCategoria,
    PatrimonioFoto,
    PatrimonioLocal,
    PatrimonioQrCode,
)


# ─────────────────────────── Lista / Detalhes / Form ───────────────────────────


@login_required
def patrimonio_list(request):
    search = (request.GET.get("q") or "").strip()
    situacao = (request.GET.get("situacao") or "").strip()
    categoria = (request.GET.get("categoria") or "").strip()
    local = (request.GET.get("local") or "").strip()

    qs = Patrimonio.objects.select_related("categoria", "local", "qrcode").order_by("-id")

    if search:
        qs = qs.filter(
            Q(numero_patrimonio__icontains=search)
            | Q(descricao__icontains=search)
            | Q(marca__icontains=search)
            | Q(modelo__icontains=search)
        )
    if situacao:
        qs = qs.filter(situacao=situacao)
    if categoria:
        qs = qs.filter(categoria_id=categoria)
    if local:
        qs = qs.filter(local_id=local)

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get("page"))

    categorias = PatrimonioCategoria.all_tenants.filter(ativo=True).order_by("nome")
    locais = PatrimonioLocal.objects.order_by("nome")

    filtros = {"search": search, "situacao": situacao, "categoria": categoria, "local": local}
    tem_filtro = any(filtros.values())

    return render(
        request,
        "patrimonio/list.html",
        {
            "page": page,
            "patrimonios": page.object_list,
            "categorias": categorias,
            "locais": locais,
            "filtros": filtros,
            "tem_filtro": tem_filtro,
            "situacoes": Patrimonio.SITUACAO_CHOICES,
        },
    )


@login_required
def patrimonio_detail(request, pk: int):
    p = get_object_or_404(
        Patrimonio.objects.select_related("categoria", "local", "secretaria", "setor", "criado_por", "qrcode"),
        pk=pk,
    )
    fotos = PatrimonioFoto.objects.filter(patrimonio=p).order_by("-principal", "ordem", "id")
    return render(
        request,
        "patrimonio/detail.html",
        {"p": p, "fotos": fotos},
    )


@login_required
@require_http_methods(["GET", "POST"])
def patrimonio_create(request):
    if request.method == "POST":
        form = PatrimonioForm(request.POST)
        if form.is_valid():
            p: Patrimonio = form.save(commit=False)
            p.criado_por = request.user
            p.save()
            messages.success(request, f"Patrimônio {p.numero_patrimonio} cadastrado.")
            return redirect("patrimonio:detail", pk=p.pk)
    else:
        form = PatrimonioForm()
    return render(request, "patrimonio/form.html", {"form": form, "editing": None})


@login_required
@require_http_methods(["GET", "POST"])
def patrimonio_edit(request, pk: int):
    p = get_object_or_404(Patrimonio, pk=pk)
    if request.method == "POST":
        form = PatrimonioForm(request.POST, instance=p)
        if form.is_valid():
            form.save()
            messages.success(request, f"Patrimônio {p.numero_patrimonio} atualizado.")
            return redirect("patrimonio:detail", pk=p.pk)
    else:
        form = PatrimonioForm(instance=p)
    return render(request, "patrimonio/form.html", {"form": form, "editing": p})


@login_required
@require_POST
def patrimonio_delete(request, pk: int):
    p = get_object_or_404(Patrimonio, pk=pk)
    numero = p.numero_patrimonio
    p.delete()
    messages.success(request, f"Patrimônio {numero} excluído.")
    return redirect("patrimonio:list")


# ─────────────────────────── Categorias (MCASP) ───────────────────────────


@login_required
def categoria_list(request):
    qs = PatrimonioCategoria.all_tenants.order_by("nome")
    search = (request.GET.get("q") or "").strip()
    if search:
        qs = qs.filter(Q(nome__icontains=search) | Q(codigo_mcasp__icontains=search))

    editing = None
    edit_pk = request.GET.get("editar")
    if edit_pk:
        editing = get_object_or_404(PatrimonioCategoria, pk=edit_pk)

    show_modal = request.GET.get("novo") == "1" or bool(editing)
    form = PatrimonioCategoriaForm(instance=editing) if show_modal else None

    return render(
        request,
        "patrimonio/categoria_list.html",
        {
            "categorias": qs,
            "search": search,
            "form": form,
            "editing": editing,
            "show_modal": show_modal,
        },
    )


@login_required
@require_POST
def categoria_save(request, pk: int | None = None):
    instance = get_object_or_404(PatrimonioCategoria, pk=pk) if pk else PatrimonioCategoria()
    form = PatrimonioCategoriaForm(request.POST, instance=instance)
    if form.is_valid():
        cat = form.save()
        messages.success(request, f"Categoria {cat.nome} {'atualizada' if pk else 'cadastrada'}.")
        return redirect("patrimonio:categoria_list")
    return render(
        request,
        "patrimonio/categoria_list.html",
        {
            "categorias": PatrimonioCategoria.all_tenants.order_by("nome"),
            "search": "",
            "form": form,
            "editing": instance if pk else None,
            "show_modal": True,
        },
        status=422,
    )


@login_required
@require_POST
def categoria_delete(request, pk: int):
    cat = get_object_or_404(PatrimonioCategoria, pk=pk)
    if cat.patrimonios.exists():
        messages.error(request, f"Categoria '{cat.nome}' tem patrimônios vinculados — não pode ser excluída.")
    else:
        cat.delete()
        messages.success(request, f"Categoria '{cat.nome}' excluída.")
    return redirect("patrimonio:categoria_list")


# ─────────────────────────── Locais ───────────────────────────


@login_required
def local_list(request):
    qs = PatrimonioLocal.objects.select_related("parent", "secretaria", "setor").order_by("nome")
    search = (request.GET.get("q") or "").strip()
    if search:
        qs = qs.filter(Q(nome__icontains=search) | Q(endereco__icontains=search))

    editing = None
    edit_pk = request.GET.get("editar")
    if edit_pk:
        editing = get_object_or_404(PatrimonioLocal, pk=edit_pk)

    show_modal = request.GET.get("novo") == "1" or bool(editing)
    form = PatrimonioLocalForm(instance=editing) if show_modal else None

    return render(
        request,
        "patrimonio/local_list.html",
        {
            "locais": qs,
            "search": search,
            "form": form,
            "editing": editing,
            "show_modal": show_modal,
        },
    )


@login_required
@require_POST
def local_save(request, pk: int | None = None):
    instance = get_object_or_404(PatrimonioLocal, pk=pk) if pk else PatrimonioLocal()
    form = PatrimonioLocalForm(request.POST, instance=instance)
    if form.is_valid():
        loc = form.save()
        messages.success(request, f"Local '{loc.nome}' {'atualizado' if pk else 'cadastrado'}.")
        return redirect("patrimonio:local_list")
    return render(
        request,
        "patrimonio/local_list.html",
        {
            "locais": PatrimonioLocal.objects.select_related("parent").order_by("nome"),
            "search": "",
            "form": form,
            "editing": instance if pk else None,
            "show_modal": True,
        },
        status=422,
    )


@login_required
@require_POST
def local_delete(request, pk: int):
    loc = get_object_or_404(PatrimonioLocal, pk=pk)
    if loc.patrimonios.exists() or loc.children.exists():
        messages.error(request, f"Local '{loc.nome}' tem patrimônios ou sub-locais — não pode ser excluído.")
    else:
        loc.delete()
        messages.success(request, f"Local '{loc.nome}' excluído.")
    return redirect("patrimonio:local_list")
