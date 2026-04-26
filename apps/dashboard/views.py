from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.organizacoes.models import Secretaria, Setor


@login_required
def home(request):
    tenant = request.tenant
    metricas = {
        "secretarias": Secretaria.objects.count() if tenant else 0,
        "setores": Setor.objects.count() if tenant else 0,
    }
    return render(request, "dashboard/home.html", {"metricas": metricas})
