from django import forms

from .models import AgentToken, RemoteCommand


class AgentTokenForm(forms.ModelForm):
    class Meta:
        model = AgentToken
        fields = (
            "name", "hostname", "secretaria", "setor",
            "description", "active", "is_canary",
        )
        widgets = {
            "name": forms.TextInput(attrs={"class": "input"}),
            "hostname": forms.TextInput(attrs={"class": "input"}),
            "secretaria": forms.Select(attrs={"class": "input"}),
            "setor": forms.Select(attrs={"class": "input"}),
            "description": forms.Textarea(attrs={"class": "input", "rows": 3}),
            "active": forms.CheckboxInput(attrs={"class": "checkbox"}),
            "is_canary": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }


class SendCommandForm(forms.Form):
    cmd_type = forms.ChoiceField(
        choices=[(k, v["label"]) for k, v in RemoteCommand.COMMANDS.items()],
        label="Comando",
        widget=forms.Select(attrs={"class": "input"}),
    )
    cmd_payload = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "input", "rows": 3, "placeholder": '{"key": "value"}'}),
        label="Payload (JSON)",
        max_length=2000,
    )
