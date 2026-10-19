from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User
from .phone import normalize_ke_phone


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(
        label="Phone number",
        max_length=20,
        required=True,    # everyone gives a number; only landlords verify it by SMS
        widget=forms.TextInput(
            attrs={"type": "tel", "inputmode": "tel", "autocomplete": "tel", "placeholder": "0712 345 678"}
        ),
    )
    role = forms.ChoiceField(
        choices=User.Role.choices,
        label="I am a",
        initial=User.Role.TENANT,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "role", "phone_number")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. "
                "Try logging in, or use 'Forgot your password?'."
            )
        return email

    def clean_phone_number(self):
        # Stored in international format, e.g. +254712345678
        phone = normalize_ke_phone(self.cleaned_data["phone_number"])
        if phone is None:
            raise forms.ValidationError("Enter a valid Kenyan phone number, for example 0712 345 678.")
        return phone


class VerifyCodeForm(forms.Form):
    code = forms.CharField(
        label="6-digit code",
        min_length=6,
        max_length=6,
        widget=forms.TextInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "one-time-code",
                "placeholder": "123456",
            }
        ),
    )

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code.isdigit():
            raise forms.ValidationError("The code is 6 digits.")
        return code