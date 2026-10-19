import json

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from . import phone as phone_service
from .forms import RegisterForm, VerifyCodeForm
from .models import PendingRegistration, User
from .otp import (
    PhoneNotVerified,
    can_send_code,
    complete_registration,
    issue_new_code,
    mask_email,
    purge_expired,
    send_code_email,
    start_registration,
    verify_code,
)

MODEL_BACKEND = "django.contrib.auth.backends.ModelBackend"
SESSION_KEY = "pending_registration_token"


def _home_for(user):
    return "properties:my_houses" if user.is_landlord else "properties:house_list"


def _pending_from_session(request):
    """The sign-up this browser started (only this browser can finish it)."""
    purge_expired()
    token = request.session.get(SESSION_KEY)
    if not token:
        return None
    return PendingRegistration.objects.filter(token=token).first()


class RoleLoginView(LoginView):
    """Landlords land on their houses after login, tenants on the search page."""

    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        # Honour ?next= (e.g. after being sent here from "Send inquiry")
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        return reverse(_home_for(self.request.user))


def register(request):
    """Step 1: collect the details and email a code. No User is created yet."""
    if request.user.is_authenticated:
        return redirect("properties:house_list")

    # ?role=landlord (from the "List your house" link) preselects the role.
    initial_role = request.GET.get("role")
    initial = {"role": initial_role} if initial_role in User.Role.values else {}
    form = RegisterForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        purge_expired()
        email = form.cleaned_data["email"]
        existing = PendingRegistration.objects.filter(email=email).first()

        # Landlords must have verified their phone by SMS in THIS browser, for exactly this number.
        # Tenants are verified by email only: their number is format-checked but not confirmed by SMS.
        is_landlord = form.cleaned_data["role"] == User.Role.LANDLORD
        phone_token = request.session.get(phone_service.SESSION_KEY) if is_landlord else ""
        phone_check = (
            phone_service.verified_row_for(phone_token, form.cleaned_data["phone_number"]) if is_landlord else None
        )

        if is_landlord and phone_check is None:
            form.add_error(
                "phone_number",
                "Please verify this phone number first: press Confirm Phone Number and enter the code we send by SMS.",
            )
        elif existing and not can_send_code(existing):
            # Stops email flooding and stops someone overwriting a sign-up in progress.
            form.add_error("email", "A code was just sent to this email. Please wait a minute and try again.")
        else:
            pending, code = start_registration(
                form.cleaned_data, phone_token=phone_check.token if phone_check else ""
            )
            sent = send_code_email(pending.email, pending.username, code)
            request.session[SESSION_KEY] = pending.token

            if sent:
                messages.success(request, f"We emailed a 6-digit code to {mask_email(pending.email)}.")
            else:
                messages.error(
                    request,
                    "We could not send the email just now. Press 'Send a new code' to try again.",
                )
            return redirect("accounts:verify_email")

    submitted = phone_service.normalize_ke_phone(request.POST.get("phone_number")) if request.method == "POST" else None
    verified = phone_service.verified_phone(request)
    return render(
        request,
        "accounts/register.html",
        {"form": form, "phone_initially_verified": bool(verified and verified == submitted)},
    )


def verify_email(request):
    """Step 2: the correct code creates the real account."""
    pending = _pending_from_session(request)
    if pending is None:
        messages.error(request, "We could not find your sign-up, or it expired. Please register again.")
        return redirect("accounts:register")

    form = VerifyCodeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ok, error = verify_code(pending, form.cleaned_data["code"])
        if ok:
            try:
                user = complete_registration(pending)
            except IntegrityError:
                # Someone took the username or email while this sign-up was waiting.
                pending.delete()
                request.session.pop(SESSION_KEY, None)
                messages.error(
                    request,
                    "That username or email was taken while you were verifying. Please register again.",
                )
                return redirect("accounts:register")
            except PhoneNotVerified:
                # The SMS verification expired or was already used.
                pending.delete()
                request.session.pop(SESSION_KEY, None)
                messages.error(
                    request,
                    "Your phone verification expired. Please register again and verify your phone number.",
                )
                return redirect("accounts:register")

            request.session.pop(SESSION_KEY, None)
            login(request, user, backend=MODEL_BACKEND)
            messages.success(request, f"Email verified. Welcome to Saka Keja, {user.username}!")
            if user.is_landlord:
                return redirect("properties:house_create")
            return redirect("properties:house_list")

        form.add_error(None, error)

    return render(
        request,
        "accounts/verify_email.html",
        {"form": form, "email_masked": mask_email(pending.email)},
    )


@require_POST
def resend_code(request):
    pending = _pending_from_session(request)
    if pending is None:
        messages.error(request, "We could not find your sign-up, or it expired. Please register again.")
        return redirect("accounts:register")

    if can_send_code(pending):
        code = issue_new_code(pending)
        send_code_email(pending.email, pending.username, code)
        messages.success(request, f"We sent a new code to {mask_email(pending.email)}.")
    else:
        messages.error(request, "Please wait a minute before asking for another code.")
    return redirect("accounts:verify_email")


# ---------- Phone verification (called by the registration page's JavaScript) ----------

def _payload(request):
    try:
        data = json.loads(request.body or b"{}")
        return data if isinstance(data, dict) else {}
    except ValueError:
        return request.POST


def _phone_response(action, request, *args):
    try:
        return JsonResponse(action(request, *args))
    except phone_service.PhoneError as error:
        body = {"ok": False, "code": error.code, "message": error.message, **error.extra}
        return JsonResponse(body, status=error.status)


@require_POST
def phone_send(request):
    raw = str(_payload(request).get("phone", "")).strip()
    if not raw:
        return JsonResponse({"ok": False, "code": "empty", "message": "Enter your phone number first."}, status=400)
    return _phone_response(phone_service.send_code, request, raw)


@require_POST
def phone_verify(request):
    return _phone_response(phone_service.verify_code, request, str(_payload(request).get("code", "")))


@require_POST
def phone_reset(request):
    return JsonResponse(phone_service.reset(request))