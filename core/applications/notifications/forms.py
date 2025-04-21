

from django import forms
from core.applications.notifications.models import Messages


class MessageForm(forms.ModelForm):
    class Meta:
        model = Messages
        fields = ["subject", "body"]
        widgets = {
            "body": forms.Textarea(attrs={"rows": 4}),
        }