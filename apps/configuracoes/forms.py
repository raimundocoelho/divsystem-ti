from django import forms

from .models import Setting


class SettingForm(forms.ModelForm):
    class Meta:
        model = Setting
        fields = ("key", "value")
        widgets = {
            "key": forms.TextInput(attrs={"class": "input", "maxlength": 255}),
            "value": forms.Textarea(attrs={"class": "input", "rows": 4}),
        }
