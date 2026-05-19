import re

from django import forms
from django.core.exceptions import ValidationError

from .models import DiarioBordo, ManutencaoTipo, Veiculo


_INPUT = {"class": "input"}
_SELECT = {"class": "input"}

_PLACA_MERCOSUL = re.compile(r"^[A-Z]{3}-?\d[A-Z0-9]\d{2}$")
_PLACA_ANTIGA = re.compile(r"^[A-Z]{3}-?\d{4}$")
_CHASSI = re.compile(r"^[A-HJ-NPR-Z0-9]{17}$")


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = [
            "secretaria", "nome", "placa", "modelo",
            "renavam", "chassi", "capacidade_passageiros", "observacoes",
        ]
        widgets = {
            "secretaria": forms.Select(attrs=_SELECT),
            "nome": forms.TextInput(attrs={**_INPUT, "placeholder": "Opcional. Identificador amigável."}),
            "placa": forms.TextInput(attrs={**_INPUT, "placeholder": "SHV-5H6S"}),
            "modelo": forms.TextInput(attrs={**_INPUT, "placeholder": "C3 AIRCROSS"}),
            "renavam": forms.TextInput(attrs={**_INPUT, "placeholder": "11 dígitos", "maxlength": "11"}),
            "chassi": forms.TextInput(attrs={**_INPUT, "placeholder": "17 caracteres", "maxlength": "17"}),
            "capacidade_passageiros": forms.NumberInput(
                attrs={**_INPUT, "min": 1, "max": 80, "placeholder": "Não conta o motorista."}
            ),
            "observacoes": forms.Textarea(attrs={**_INPUT, "rows": 2}),
        }

    def clean_placa(self):
        placa = (self.cleaned_data.get("placa") or "").strip().upper()
        if not placa:
            raise ValidationError("Informe a placa do veículo.")
        normalizada = placa.replace("-", "")
        if not (_PLACA_MERCOSUL.match(placa) or _PLACA_ANTIGA.match(placa)
                or _PLACA_MERCOSUL.match(normalizada) or _PLACA_ANTIGA.match(normalizada)):
            raise ValidationError("Placa inválida. Use o formato AAA-1234 ou AAA-1B23.")
        return placa

    def clean_renavam(self):
        renavam = (self.cleaned_data.get("renavam") or "").strip()
        if not renavam:
            return ""
        digits = re.sub(r"\D", "", renavam)
        if len(digits) != 11:
            raise ValidationError("RENAVAM deve ter exatamente 11 dígitos.")
        return digits

    def clean_chassi(self):
        chassi = (self.cleaned_data.get("chassi") or "").strip().upper()
        chassi = re.sub(r"\s+", "", chassi)
        if not chassi:
            return ""
        if not _CHASSI.match(chassi):
            raise ValidationError("Chassi inválido. 17 caracteres alfanuméricos (sem I, O, Q).")
        return chassi

    def clean(self):
        cleaned = super().clean()
        instance = self.instance
        tenant_id = getattr(instance, "tenant_id", None)
        if tenant_id is None:
            from apps.core.threadlocal import get_current_tenant
            t = get_current_tenant()
            tenant_id = t.pk if t else None

        for field, label in [("placa", "placa"), ("renavam", "RENAVAM"), ("chassi", "chassi")]:
            value = cleaned.get(field)
            if not value or tenant_id is None:
                continue
            qs = Veiculo.all_tenants.filter(tenant_id=tenant_id, **{field: value})
            if instance.pk:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                self.add_error(field, f"Já existe um veículo com esse {label} nesta organização.")
        return cleaned


class DiarioBordoForm(forms.ModelForm):
    class Meta:
        model = DiarioBordo
        fields = [
            "veiculo", "condutor", "autorizador", "viagem_transporte",
            "saida_em", "retorno_em", "km_saida", "km_retorno",
            "destino", "finalidade",
        ]
        widgets = {
            "veiculo": forms.Select(attrs=_SELECT),
            "condutor": forms.Select(attrs=_SELECT),
            "autorizador": forms.Select(attrs=_SELECT),
            "viagem_transporte": forms.Select(attrs=_SELECT),
            "saida_em": forms.DateTimeInput(attrs={**_INPUT, "type": "datetime-local"}),
            "retorno_em": forms.DateTimeInput(attrs={**_INPUT, "type": "datetime-local"}),
            "km_saida": forms.NumberInput(attrs={**_INPUT, "min": 0}),
            "km_retorno": forms.NumberInput(attrs={**_INPUT, "min": 0, "placeholder": "Preencha no retorno"}),
            "destino": forms.TextInput(attrs={**_INPUT, "placeholder": "Ex: Goma, Senna, Ubá"}),
            "finalidade": forms.Textarea(attrs={**_INPUT, "rows": 2, "placeholder": "Ex: curativo domiciliar, visita ACS"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.accounts.models import User
        self.fields["condutor"].queryset = User.objects.order_by("name")
        self.fields["autorizador"].queryset = User.objects.order_by("name")
        self.fields["viagem_transporte"].required = False
        self.fields["viagem_transporte"].empty_label = "Não vincular — viagem avulsa"

    def clean(self):
        cleaned = super().clean()
        saida = cleaned.get("saida_em")
        retorno = cleaned.get("retorno_em")
        km_saida = cleaned.get("km_saida")
        km_retorno = cleaned.get("km_retorno")

        if saida and retorno and retorno <= saida:
            self.add_error("retorno_em", "O retorno precisa ser posterior à saída.")

        if km_saida is not None and km_retorno is not None and km_retorno < km_saida:
            self.add_error("km_retorno", "KM de retorno deve ser maior ou igual ao KM de saída.")

        return cleaned


class RelatorioFrotaFiltroForm(forms.Form):
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={**_INPUT, "type": "date"}),
    )
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={**_INPUT, "type": "date"}),
    )
    secretaria = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="Todas as secretarias",
        widget=forms.Select(attrs=_SELECT),
    )
    veiculo = forms.ModelChoiceField(
        queryset=Veiculo.objects.none(),
        required=False,
        empty_label="Toda a frota",
        widget=forms.Select(attrs=_SELECT),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.organizacoes.models import Secretaria
        self.fields["secretaria"].queryset = Secretaria.objects.filter(ativo=True).order_by("nome")
        sec = self.data.get("secretaria") if self.data else None
        veiculos = Veiculo.objects.order_by("placa")
        if sec:
            veiculos = veiculos.filter(secretaria_id=sec)
        self.fields["veiculo"].queryset = veiculos

    def clean(self):
        cleaned = super().clean()
        di = cleaned.get("data_inicio")
        df = cleaned.get("data_fim")
        if di and df and df < di:
            self.add_error("data_fim", "Data final deve ser igual ou posterior à inicial.")
        return cleaned
