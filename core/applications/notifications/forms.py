from django import forms

from core.applications.notifications.models import Message


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["receiver", "subject", "message", "property"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        self.sender = kwargs.pop("sender", None)
        super().__init__(*args, **kwargs)

        # If sender is provided, exclude them from receiver choices
        if self.sender:
            self.fields["receiver"].queryset = self.fields["receiver"].queryset.exclude(
                id=self.sender.id,
            )

        # Make receiver field not required if we're pre-filling it
        if "initial" in kwargs and "receiver" in kwargs["initial"]:
            self.fields["receiver"].required = False


class ReplyForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 4}),
        }
