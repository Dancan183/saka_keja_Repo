from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    role = forms.ChoiceField(
        choices=User.Role.choices,
        label="I am a",
        initial=User.Role.TENANT,
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "phone_number", "role")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists. "
                "Try logging in, or use 'Forgot your password?'."
            )
        return email

    def clean(self):
        cleaned = super().clean()
        # Landlords must be reachable by tenants.
        if cleaned.get("role") == User.Role.LANDLORD and not cleaned.get("phone_number"):
            self.add_error("phone_number", "Landlords must provide a phone number.")
        return cleaned


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