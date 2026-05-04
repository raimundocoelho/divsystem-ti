from django import forms

from apps.mikrotik.models import Comando, Device, Equipamento, _normalize_mac


_INPUT = {"class": "input"}
_SELECT = {"class": "input"}
_TEXTAREA = {"class": "input font-mono", "rows": 6}


class EquipamentoForm(forms.ModelForm):
    class Meta:
        model = Equipamento
        fields = [
            "nome",
            "descricao",
            "modelo",
            "serial_number",
            "mac_address",
            "secretaria",
            "setor",
            "endereco",
        ]
        widgets = {
            "nome": forms.TextInput(attrs=_INPUT),
            "descricao": forms.TextInput(attrs=_INPUT),
            "modelo": forms.Select(attrs=_SELECT),
            "serial_number": forms.TextInput(attrs=_INPUT),
            "mac_address": forms.TextInput(attrs={**_INPUT, "placeholder": "AA:BB:CC:DD:EE:FF"}),
            "secretaria": forms.Select(attrs=_SELECT),
            "setor": forms.Select(attrs=_SELECT),
            "endereco": forms.TextInput(attrs=_INPUT),
        }


class EnviarComandoForm(forms.Form):
    TIPO_CHOICES = Comando.TIPO_CHOICES

    tipo = forms.ChoiceField(
        choices=TIPO_CHOICES,
        initial="rest_get",
        widget=forms.Select(attrs=_SELECT),
    )
    path = forms.CharField(
        max_length=512,
        widget=forms.TextInput(attrs={**_INPUT, "placeholder": "/system/identity"}),
        help_text="Ex.: /system/identity, /interface, /ip/address. Para 'execute', "
        "um script RouterOS completo.",
    )
    payload = forms.CharField(
        widget=forms.Textarea(attrs={**_TEXTAREA, "placeholder": '{"key":"value"}'}),
        required=False,
        help_text="JSON. Vazio para GET/DELETE.",
    )

    def clean_payload(self):
        import json

        raw = (self.cleaned_data.get("payload") or "").strip()
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(f"JSON inválido: {exc}") from exc


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = [
            "nome",
            "tipo",
            "mac_address",
            "ip_address",
            "hostname",
            "secretaria",
            "setor",
            "responsavel",
            "descricao",
            "status",
        ]
        widgets = {
            "nome": forms.TextInput(attrs={**_INPUT, "placeholder": "PC-Recepcao, Impressora-RH..."}),
            "tipo": forms.Select(attrs=_SELECT),
            "mac_address": forms.TextInput(attrs={**_INPUT, "placeholder": "AA:BB:CC:DD:EE:FF"}),
            "ip_address": forms.TextInput(attrs={**_INPUT, "placeholder": "192.168.88.10"}),
            "hostname": forms.TextInput(attrs={**_INPUT, "placeholder": "(detectado pelo DHCP)"}),
            "secretaria": forms.Select(attrs=_SELECT),
            "setor": forms.Select(attrs=_SELECT),
            "responsavel": forms.TextInput(attrs={**_INPUT, "placeholder": "Nome da pessoa"}),
            "descricao": forms.TextInput(attrs=_INPUT),
            "status": forms.Select(attrs=_SELECT),
        }

    def clean_mac_address(self):
        return _normalize_mac(self.cleaned_data["mac_address"])


# === Políticas de filtro ===
class PoliticaForm(forms.ModelForm):
    class Meta:
        from apps.mikrotik.models import Politica  # local import pra evitar ciclo

        model = Politica
        fields = ["nome", "descricao", "ativo"]
        widgets = {
            "nome": forms.TextInput(attrs={**_INPUT, "placeholder": "Bloqueio Redes Sociais"}),
            "descricao": forms.TextInput(attrs={**_INPUT, "placeholder": "Para uso em horário comercial"}),
        }


class RegraDominioForm(forms.ModelForm):
    class Meta:
        from apps.mikrotik.models import RegraDominio

        model = RegraDominio
        fields = ["dominio", "incluir_subdominios", "comentario"]
        widgets = {
            "dominio": forms.TextInput(attrs={**_INPUT, "placeholder": "facebook.com"}),
            "comentario": forms.TextInput(attrs={**_INPUT, "placeholder": "(opcional)"}),
        }


class PoliticaAlvoForm(forms.Form):
    """Form pra adicionar Device como alvo. Filtra devices por equipamento."""
    device = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs=_SELECT),
        empty_label="-- escolha um device --",
    )

    def __init__(self, *args, equipamento=None, exclude_devices=None, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.mikrotik.models import Device

        qs = Device.objects.filter(equipamento=equipamento, status="ativo")
        if exclude_devices:
            qs = qs.exclude(pk__in=exclude_devices)
        self.fields["device"].queryset = qs.order_by("nome")
