"""Forms do módulo Patrimônio — paridade com o painel Laravel."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import forms

from .models import Patrimonio, PatrimonioCategoria, PatrimonioLocal


_INPUT = {"class": "input"}
_SELECT = {"class": "input"}


def _parse_decimal_br(value: str) -> Decimal | None:
    if value is None or value == "":
        return None
    s = str(value).strip()
    if not s:
        return None
    # "1.234,56" → "1234.56"
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        raise forms.ValidationError("Valor inválido. Use o formato 1234,56.")


class PatrimonioForm(forms.ModelForm):
    valor_aquisicao = forms.CharField(
        widget=forms.TextInput(attrs={**_INPUT, "placeholder": "1234,56"})
    )

    class Meta:
        model = Patrimonio
        fields = [
            "descricao", "categoria", "local",
            "marca", "modelo", "numero_serie", "cor",
            "valor_aquisicao", "data_aquisicao", "nota_fiscal_numero",
            "estado_conservacao", "situacao",
            "observacoes",
        ]
        widgets = {
            "descricao": forms.TextInput(attrs={**_INPUT, "placeholder": "Cadeira giratória presidente"}),
            "categoria": forms.Select(attrs=_SELECT),
            "local": forms.Select(attrs=_SELECT),
            "marca": forms.TextInput(attrs=_INPUT),
            "modelo": forms.TextInput(attrs=_INPUT),
            "numero_serie": forms.TextInput(attrs=_INPUT),
            "cor": forms.TextInput(attrs={**_INPUT, "placeholder": "Preto"}),
            "data_aquisicao": forms.DateInput(attrs={**_INPUT, "type": "date"}),
            "nota_fiscal_numero": forms.TextInput(attrs={**_INPUT, "placeholder": "NF-123456"}),
            "estado_conservacao": forms.Select(attrs=_SELECT),
            "situacao": forms.Select(attrs=_SELECT),
            "observacoes": forms.Textarea(attrs={**_INPUT, "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = (
            PatrimonioCategoria.all_tenants
            .filter(ativo=True)
            .order_by("nome")
        )
        self.fields["local"].queryset = PatrimonioLocal.objects.select_related("parent").order_by("nome")
        self.fields["local"].required = False
        self.fields["local"].empty_label = "Nenhum"
        # situacao só é editável em edição (espelha o Laravel)
        if not self.instance.pk:
            self.fields.pop("situacao", None)

    def clean_valor_aquisicao(self):
        val = _parse_decimal_br(self.cleaned_data.get("valor_aquisicao"))
        if val is None:
            raise forms.ValidationError("Informe o valor de aquisição.")
        if val < 0:
            raise forms.ValidationError("Valor não pode ser negativo.")
        return val


class PatrimonioCategoriaForm(forms.ModelForm):
    class Meta:
        model = PatrimonioCategoria
        fields = [
            "nome", "codigo_mcasp", "nome_conta_pcasp",
            "vida_util_anos", "taxa_depreciacao_anual", "valor_residual_pct",
            "metodo_depreciacao", "deprecia", "ativo",
        ]
        widgets = {
            "nome": forms.TextInput(attrs=_INPUT),
            "codigo_mcasp": forms.TextInput(attrs={**_INPUT, "placeholder": "1.2.3.1.1.05.00"}),
            "nome_conta_pcasp": forms.TextInput(attrs=_INPUT),
            "vida_util_anos": forms.NumberInput(attrs={**_INPUT, "min": 0}),
            "taxa_depreciacao_anual": forms.NumberInput(attrs={**_INPUT, "step": "0.01", "min": 0}),
            "valor_residual_pct": forms.NumberInput(attrs={**_INPUT, "step": "0.01", "min": 0}),
            "metodo_depreciacao": forms.Select(attrs=_SELECT),
        }


class PatrimonioLocalForm(forms.ModelForm):
    class Meta:
        model = PatrimonioLocal
        fields = ["nome", "tipo", "parent", "secretaria", "setor", "endereco"]
        widgets = {
            "nome": forms.TextInput(attrs=_INPUT),
            "tipo": forms.Select(attrs=_SELECT),
            "parent": forms.Select(attrs=_SELECT),
            "secretaria": forms.Select(attrs=_SELECT),
            "setor": forms.Select(attrs=_SELECT),
            "endereco": forms.TextInput(attrs=_INPUT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = PatrimonioLocal.objects.order_by("nome")
        self.fields["parent"].required = False
        self.fields["parent"].empty_label = "Nenhum (raiz)"
        for f in ("secretaria", "setor", "parent"):
            self.fields[f].required = False
