import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import PendingRegistration, User

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_LIFETIME = timedelta(minutes=10)       # how long one code works
PENDING_LIFETIME = timedelta(minutes=30)   # how long a sign-up can wait in total
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_ATTEMPTS = 5


def _hash(code):
    return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def _new_code():
    return f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"


def purge_expired():
    """Remove sign-ups that were never verified in time."""
    PendingRegistration.objects.filter(created_at__lt=timezone.now() - PENDING_LIFETIME).delete()


def can_send_code(pending):
    return timezone.now() - pending.code_sent_at >= RESEND_COOLDOWN


def start_registration(data):
    """
    Store the sign-up details (NOT as a User) and return (pending, plain_code).
    A new sign-up for the same email replaces the old pending one.
    """
    code = _new_code()
    now = timezone.now()
    pending, _ = PendingRegistration.objects.update_or_create(
        email=data["email"],
        defaults={
            "token": secrets.token_urlsafe(32),
            "username": data["username"],
            "password_hash": make_password(data["password1"]),
            "phone_number": data.get("phone_number", ""),
            "role": data["role"],
            "code_hash": _hash(code),
            "attempts": 0,
            "code_sent_at": now,
            "created_at": now,
        },
    )
    return pending, code


def issue_new_code(pending):
    code = _new_code()
    pending.code_hash = _hash(code)
    pending.attempts = 0
    pending.code_sent_at = timezone.now()
    pending.save(update_fields=["code_hash", "attempts", "code_sent_at"])
    return code


def verify_code(pending, code):
    """Return (ok, error_message). Does not create the user."""
    code = (code or "").strip()
    now = timezone.now()

    if now - pending.created_at > PENDING_LIFETIME:
        return False, "Your sign-up expired. Please register again."
    if now - pending.code_sent_at > OTP_LIFETIME:
        return False, "That code has expired. Please request a new one."
    if pending.attempts >= MAX_ATTEMPTS:
        return False, "Too many wrong attempts. Please request a new code."

    pending.attempts += 1
    pending.save(update_fields=["attempts"])
    if hmac.compare_digest(pending.code_hash, _hash(code)):
        return True, ""
    return False, "That code is not correct."


def complete_registration(pending):
    """Create the real User from the verified sign-up. May raise IntegrityError."""
    with transaction.atomic():
        user = User(
            username=pending.username,
            email=pending.email,
            phone_number=pending.phone_number,
            role=pending.role,
        )
        user.password = pending.password_hash  # already hashed
        user.save()
        pending.delete()
    return user


def mask_email(email):
    name, _, domain = email.partition("@")
    return f"{name[:1]}***@{domain}"


def send_code_email(email, username, code):
    """Email the code. Returns True if it was handed to the mail server."""
    minutes = int(OTP_LIFETIME.total_seconds() // 60)
    message = (
        f"Hello {username},\n\n"
        f"Your Saka Keja verification code is: {code}\n\n"
        f"It expires in {minutes} minutes. "
        "If you did not create an account, you can ignore this email.\n"
    )
    try:
        send_mail("Your Saka Keja verification code", message, None, [email])
        return True
    except Exception:
        logger.exception("Could not send verification email")
        return False