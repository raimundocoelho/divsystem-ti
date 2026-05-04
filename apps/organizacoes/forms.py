from django import forms

from apps.core.models import RESERVED_SLUGS, Tenant

from .models import Secretaria, Setor


_input_classes = "input"


class TenantForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = (
            "name", "slug", "external_code", "cnpj", "email", "phone",
            "contact_name", "address", "city", "state", "active",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": _input_classes, "placeholder": "Ex: Prefeitura Municipal de Cedral"}),
            "slug": forms.TextInput(attrs={"class": _input_classes, "placeholder": "Ex: divinesia"}),
            "external_code": forms.TextInput(attrs={"class": _input_classes, "placeholder": "Ex: 6916570"}),
            "cnpj": forms.TextInput(attrs={"class": _input_classes, "placeholder": "00.000.000/0000-00"}),
            "email": forms.EmailInput(attrs={"class": _input_classes, "placeholder": "ti@prefeitura.gov.br"}),
            "phone": forms.TextInput(attrs={"class": _input_classes, "placeholder": "(99) 99999-9999"}),
            "contact_name": forms.TextInput(attrs={"class": _input_classes, "placeholder": "Nome do contato"}),
            "address": forms.TextInput(attrs={"class": _input_classes, "placeholder": "Rua, número, bairro"}),
            "city": forms.TextInput(attrs={"class": _input_classes, "placeholder": "Ex: Cedral"}),
            "state": forms.TextInput(attrs={"class": _input_classes, "maxlength": 2, "placeholder": "MA"}),
            "active": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def clean_slug(self):
        slug = (self.cleaned_data.get("slug") or "").strip().lower()
        if slug and slug in RESERVED_SLUGS:
            raise forms.ValidationError("Slug reservado, escolha outro.")
        return slug


class SecretariaForm(forms.ModelForm):
    class Meta:
        model = Secretaria
        fields = ("nome", "codigo", "descricao", "responsavel", "ativo")
        widgets = {
            "nome": forms.TextInput(attrs={"class": _input_classes, "autofocus": "autofocus", "maxlength": 100}),
            "codigo": forms.TextInput(attrs={"class": _input_classes, "maxlength": 4, "placeholder": "0001"}),
            "descricao": forms.TextInput(attrs={"class": _input_classes, "maxlength": 255}),
            "responsavel": forms.TextInput(attrs={"class": _input_classes, "maxlength": 100}),
            "ativo": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }


class SetorForm(forms.ModelForm):
    class Meta:
        model = Setor
        fields = ("nome", "secretaria", "descricao", "responsavel", "localizacao", "ativo")
        widgets = {
            "nome": forms.TextInput(attrs={"class": _input_classes, "autofocus": "autofocus", "maxlength": 100}),
            "secretaria": forms.Select(attrs={"class": _input_classes}),
            "descricao": forms.TextInput(attrs={"class": _input_classes, "maxlength": 255}),
            "responsavel": forms.TextInput(attrs={"class": _input_classes, "maxlength": 100}),
            "localizacao": forms.TextInput(attrs={"class": _input_classes, "maxlength": 150}),
            "ativo": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["secretaria"].queryset = Secretaria.objects.filter(ativo=True).order_by("nome")
        self.fields["secretaria"].empty_label = "— sem secretaria —"
