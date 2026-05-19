from django import forms

from .models import DiarioBordo, ManutencaoTipo, Veiculo


class VeiculoForm(forms.ModelForm):
    class Meta:
        model = Veiculo
        fields = [
            "secretaria", "nome", "placa", "modelo",
            "renavam", "chassi", "capacidade_passageiros", "observacoes",
        ]
        widgets = {
            "observacoes": forms.Textarea(attrs={"rows": 3}),
        }


class DiarioBordoForm(forms.ModelForm):
    class Meta:
        model = DiarioBordo
        fields = [
            "veiculo", "condutor", "autorizador", "motorista",
            "saida_em", "km_saida", "destino", "finalidade",
            "retorno_em", "km_retorno",
        ]
        widgets = {
            "saida_em": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "retorno_em": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class ManutencaoTipoForm(forms.ModelForm):
    class Meta:
        model = ManutencaoTipo
        fields = ["nome", "descricao", "intervalo_dias", "duracao_estimada_minutos", "ativo"]
        widgets = {"descricao": forms.Textarea(attrs={"rows": 2})}
