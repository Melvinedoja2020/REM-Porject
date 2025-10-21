from django import forms


class ContactForm(forms.Form):
    INTEREST_CHOICES = [
        ("Location", "Location"),
        ("Rent", "Rent"),
        ("Sale", "Sale"),
        ("utilities", "Utilities"),
    ]

    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Your name", "id": "name"}
        ),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={"class": "form-control", "placeholder": "Email", "id": "email-contact"}
        ),
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Your phone number",
                "id": "phone",
            }
        ),
    )
    interest = forms.ChoiceField(
        choices=[("", "Select")] + INTEREST_CHOICES,
        widget=forms.Select(attrs={
            "class": "nice-select w-100",
            "tabindex": "0",
        }),
    )
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Message",
                "rows": 5,
                "id": "message",
            }
        ),
    )

    def clean_message(self):
        message = self.cleaned_data["message"]
        if len(message.strip()) < 10:
            raise forms.ValidationError("Please enter a more detailed message.")
        return message
