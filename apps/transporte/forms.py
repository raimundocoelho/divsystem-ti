"""Forms do módulo Transporte — paridade com o painel Laravel."""
from __future__ import annotations

import re
from datetime import date

from django import forms

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


_INPUT = {"class": "input"}
_SELECT = {"class": "input"}
_UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT",
        "PA","PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO"]


def _digits(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


# ───────────────────────── Cadastros simples ─────────────────────────


class CidadeDestinoForm(forms.ModelForm):
    class Meta:
        model = CidadeDestino
        fields = ["nome", "uf", "observacao", "ativo"]
        widgets = {
            "nome": forms.TextInput(attrs={**_INPUT, "placeholder": "Ex: Viçosa"}),
            "uf": forms.Select(attrs=_SELECT, choices=[(u, u) for u in _UFS]),
            "observacao": forms.TextInput(attrs=_INPUT),
        }

    def clean_nome(self):
        return (self.cleaned_data.get("nome") or "").strip()

    def clean_uf(self):
        return (self.cleaned_data.get("uf") or "").upper()


class LocalAtendimentoForm(forms.ModelForm):
    class Meta:
        model = LocalAtendimento
        fields = ["cidade_destino", "nome", "endereco", "telefone", "observacao", "ativo"]
        widgets = {
            "cidade_destino": forms.Select(attrs=_SELECT),
            "nome": forms.TextInput(attrs={**_INPUT, "placeholder": "Hospital São Sebastião"}),
            "endereco": forms.TextInput(attrs=_INPUT),
            "telefone": forms.TextInput(attrs=_INPUT),
            "observacao": forms.TextInput(attrs=_INPUT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cidade_destino"].queryset = CidadeDestino.objects.filter(ativo=True).order_by("nome")


class LocalEmbarqueForm(forms.ModelForm):
    class Meta:
        model = LocalEmbarque
        fields = ["nome", "endereco", "hora", "observacao", "ativo"]
        widgets = {
            "nome": forms.TextInput(attrs={**_INPUT, "placeholder": "Terminal Rodoviário"}),
            "endereco": forms.TextInput(attrs=_INPUT),
            "hora": forms.TimeInput(attrs={**_INPUT, "type": "time"}),
            "observacao": forms.TextInput(attrs=_INPUT),
        }


class HorarioTransporteForm(forms.ModelForm):
    class Meta:
        model = HorarioTransporte
        fields = ["hora", "descricao", "ordem", "ativo"]
        widgets = {
            "hora": forms.TimeInput(attrs={**_INPUT, "type": "time"}),
            "descricao": forms.TextInput(attrs={**_INPUT, "placeholder": "Ex: Madrugada"}),
            "ordem": forms.NumberInput(attrs={**_INPUT, "min": 0}),
        }


# ───────────────────────── Motorista ─────────────────────────


class MotoristaForm(forms.ModelForm):
    class Meta:
        model = Motorista
        fields = [
            "nome", "cpf", "cnh", "cnh_categoria", "cnh_validade",
            "telefone", "user", "observacao", "ativo",
        ]
        widgets = {
            "nome": forms.TextInput(attrs=_INPUT),
            "cpf": forms.TextInput(attrs={**_INPUT, "placeholder": "000.000.000-00"}),
            "cnh": forms.TextInput(attrs=_INPUT),
            "cnh_categoria": forms.Select(
                attrs=_SELECT,
                choices=[(c, c) for c in ["A","B","C","D","E","AB","AC","AD","AE"]],
            ),
            "cnh_validade": forms.DateInput(attrs={**_INPUT, "type": "date"}),
            "telefone": forms.TextInput(attrs={**_INPUT, "placeholder": "(31) 99999-9999"}),
            "user": forms.Select(attrs=_SELECT),
            "observacao": forms.Textarea(attrs={**_INPUT, "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User
        self.fields["user"].queryset = User.objects.order_by("name")
        self.fields["user"].required = False
        self.fields["user"].empty_label = "Sem usuário vinculado"

    def clean_cpf(self):
        v = _digits(self.cleaned_data.get("cpf"))
        if not v:
            return ""
        if len(v) != 11:
            raise forms.ValidationError("CPF deve ter 11 dígitos.")
        return v


# ───────────────────────── Paciente ─────────────────────────


class PacienteForm(forms.ModelForm):
    class Meta:
        model = Paciente
        fields = [
            "nome", "cpf", "cns", "data_nascimento", "sexo",
            "telefone", "endereco", "bairro",
            "secretaria", "unidade", "equipe", "microarea",
            "observacao", "ativo",
        ]
        widgets = {
            "nome": forms.TextInput(attrs=_INPUT),
            "cpf": forms.TextInput(attrs={**_INPUT, "placeholder": "000.000.000-00"}),
            "cns": forms.TextInput(attrs={**_INPUT, "placeholder": "15 dígitos"}),
            "data_nascimento": forms.DateInput(attrs={**_INPUT, "type": "date"}),
            "sexo": forms.Select(attrs=_SELECT, choices=[("", "—"), ("M", "Masculino"), ("F", "Feminino")]),
            "telefone": forms.TextInput(attrs=_INPUT),
            "endereco": forms.TextInput(attrs=_INPUT),
            "bairro": forms.TextInput(attrs=_INPUT),
            "secretaria": forms.Select(attrs=_SELECT),
            "unidade": forms.TextInput(attrs={**_INPUT, "placeholder": "UBS / ESF"}),
            "equipe": forms.TextInput(attrs=_INPUT),
            "microarea": forms.TextInput(attrs=_INPUT),
            "observacao": forms.Textarea(attrs={**_INPUT, "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.organizacoes.models import Secretaria
        self.fields["secretaria"].queryset = Secretaria.objects.filter(ativo=True).order_by("nome")
        self.fields["secretaria"].required = False

    def clean_cpf(self):
        v = _digits(self.cleaned_data.get("cpf"))
        if v and len(v) != 11:
            raise forms.ValidationError("CPF deve ter 11 dígitos.")
        return v

    def clean_cns(self):
        v = _digits(self.cleaned_data.get("cns"))
        if v and len(v) != 15:
            raise forms.ValidationError("CNS deve ter 15 dígitos.")
        return v


# ───────────────────────── Protocolo de Exame ─────────────────────────


class ProtocoloExameForm(forms.ModelForm):
    class Meta:
        model = ProtocoloExame
        fields = [
            "paciente", "viagem_origem", "local_atendimento",
            "tipo", "descricao", "numero_protocolo",
            "previsao_retirada", "observacoes",
        ]
        widgets = {
            "paciente": forms.Select(attrs=_SELECT),
            "viagem_origem": forms.Select(attrs=_SELECT),
            "local_atendimento": forms.Select(attrs=_SELECT),
            "tipo": forms.Select(attrs=_SELECT),
            "descricao": forms.TextInput(attrs={**_INPUT, "placeholder": "Hemograma completo"}),
            "numero_protocolo": forms.TextInput(attrs=_INPUT),
            "previsao_retirada": forms.DateInput(attrs={**_INPUT, "type": "date"}),
            "observacoes": forms.Textarea(attrs={**_INPUT, "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["paciente"].queryset = Paciente.objects.filter(ativo=True).order_by("nome")
        self.fields["viagem_origem"].queryset = ViagemTransporte.objects.order_by("-data")[:200]
        self.fields["viagem_origem"].required = False
        self.fields["viagem_origem"].empty_label = "Sem viagem vinculada"
        self.fields["local_atendimento"].queryset = LocalAtendimento.objects.filter(ativo=True).order_by("nome")
        self.fields["local_atendimento"].required = False
        self.fields["local_atendimento"].empty_label = "—"


# ───────────────────────── Viagem ─────────────────────────


class ViagemTransporteForm(forms.ModelForm):
    class Meta:
        model = ViagemTransporte
        fields = [
            "data", "hora_saida", "veiculo", "motorista",
            "cidade_destino", "horario", "tipo", "status", "observacoes",
        ]
        widgets = {
            "data": forms.DateInput(attrs={**_INPUT, "type": "date"}),
            "hora_saida": forms.TimeInput(attrs={**_INPUT, "type": "time"}),
            "veiculo": forms.Select(attrs=_SELECT),
            "motorista": forms.Select(attrs=_SELECT),
            "cidade_destino": forms.Select(attrs=_SELECT),
            "horario": forms.Select(attrs=_SELECT),
            "tipo": forms.Select(attrs=_SELECT),
            "status": forms.Select(attrs=_SELECT),
            "observacoes": forms.Textarea(attrs={**_INPUT, "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.frota.models import Veiculo
        self.fields["veiculo"].queryset = Veiculo.objects.order_by("placa")
        self.fields["motorista"].queryset = Motorista.objects.filter(ativo=True).order_by("nome")
        self.fields["cidade_destino"].queryset = CidadeDestino.objects.filter(ativo=True).order_by("nome")
        self.fields["horario"].queryset = HorarioTransporte.objects.filter(ativo=True).order_by("ordem", "hora")
        self.fields["horario"].required = False
        self.fields["horario"].empty_label = "—"


class PassageiroViagemForm(forms.ModelForm):
    class Meta:
        model = PassageiroViagem
        fields = [
            "paciente", "acompanhante", "local_atendimento", "local_embarque",
            "finalidade", "observacao",
        ]
        widgets = {
            "paciente": forms.Select(attrs=_SELECT),
            "acompanhante": forms.Select(attrs=_SELECT),
            "local_atendimento": forms.Select(attrs=_SELECT),
            "local_embarque": forms.Select(attrs=_SELECT),
            "finalidade": forms.TextInput(attrs={**_INPUT, "placeholder": "Consulta cardiologia"}),
            "observacao": forms.TextInput(attrs=_INPUT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ativos = Paciente.objects.filter(ativo=True).order_by("nome")
        self.fields["paciente"].queryset = ativos
        self.fields["acompanhante"].queryset = ativos
        self.fields["acompanhante"].required = False
        self.fields["acompanhante"].empty_label = "Sem acompanhante"
        self.fields["local_atendimento"].queryset = LocalAtendimento.objects.filter(ativo=True).order_by("nome")
        self.fields["local_atendimento"].required = False
        self.fields["local_atendimento"].empty_label = "—"
        self.fields["local_embarque"].queryset = LocalEmbarque.objects.filter(ativo=True).order_by("nome")
        self.fields["local_embarque"].required = False
        self.fields["local_embarque"].empty_label = "—"
