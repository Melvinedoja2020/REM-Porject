from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Your Name",
            },
        ),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "Your Email",
            },
        ),
    )
    subject = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Subject",
            },
        ),
    )
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "placeholder": "Your Message",
                "rows": 5,
            },
        ),
    )
