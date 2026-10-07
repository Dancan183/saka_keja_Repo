from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import LoginForm, RegisterForm, VerifyEmailForm
from .models import User
from .otp import can_resend, create_otp, send_otp_email, verify_otp

MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"


def _home_for(user):
    return "properties:my_houses" if user.is_landlord else "properties:house_list"


class RoleLoginView(LoginView):
    """Landlords land on their houses after login, tenants on the search page."""

    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        # Honour ?next= (e.g. after being sent here from "Send inquiry")
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        return reverse(_home_for(self.request.user))


def register(request):
    if request.user.is_authenticated:
        return redirect("properties:house_list")

    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.is_active = False  # cannot log in until the email is verified
        user.save()

        code = create_otp(user)
        sent = send_otp_email(user, code)
        request.session["pending_email"] = user.email

        if sent:
            messages.success(request, f"We emailed a 6-digit code to {user.email}.")
        else:
            messages.error(
                request,
                "We could not send the email just now. Press 'Send a new code' to try again.",
            )
        return redirect("accounts:verify_email")

    return render(request, "accounts/register.html", {"form": form})


def verify_email(request):
    email = request.session.get("pending_email") or request.GET.get("email", "")
    form = VerifyEmailForm(request.POST or None, initial={"email": email})

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        user = User.objects.filter(email__iexact=email, is_active=False).first()

        if user is None:
            ok, error = False, "That code is not correct."  # same message: no account hints
        else:
            ok, error = verify_otp(user, form.cleaned_data["code"])

        if ok:
            user.is_active = True
            user.save(update_fields=["is_active"])
            request.session.pop("pending_email", None)
            login(request, user, backend=MODEL_BACKEND)
            messages.success(request, f"Email verified. Welcome to Saka Keja, {user.username}!")
            if user.is_landlord:
                return redirect("properties:house_create")
            return redirect("properties:house_list")

        form.add_error(None, error)

    return render(request, "accounts/verify_email.html", {"form": form})


@require_POST
def resend_code(request):
    email = request.POST.get("email", "").strip()
    user = User.objects.filter(email__iexact=email, is_active=False).first() if email else None

    if user is not None:
        if can_resend(user):
            send_otp_email(user, create_otp(user))
            request.session["pending_email"] = user.email
        else:
            messages.error(request, "Please wait a minute before asking for another code.")
            return redirect("accounts:verify_email")

    # Same message whether or not the email exists, so nobody can probe for accounts.
    messages.success(request, "If that email is waiting for verification, we sent a new code.")
    return redirect("accounts:verify_email")