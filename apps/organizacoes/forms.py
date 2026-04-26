from django import forms

from .models import Secretaria, Setor


_input_classes = "input"


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
