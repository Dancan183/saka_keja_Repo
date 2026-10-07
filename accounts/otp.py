import hashlib
import hmac
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailOTP

logger = logging.getLogger(__name__)

OTP_LENGTH = 6
OTP_LIFETIME = timedelta(minutes=10)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_ATTEMPTS = 5


def _hash(code):
    return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def create_otp(user):
    """Invalidate older codes, store a hash of a new one, and return the plain code."""
    EmailOTP.objects.filter(user=user, used=False).update(used=True)
    code = f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"
    EmailOTP.objects.create(user=user, code_hash=_hash(code))
    return code


def can_resend(user):
    cutoff = timezone.now() - RESEND_COOLDOWN
    return not EmailOTP.objects.filter(user=user, created_at__gt=cutoff).exists()


def verify_otp(user, code):
    """Return (ok, error_message)."""
    code = (code or "").strip()
    otp = EmailOTP.objects.filter(user=user, used=False).first()

    if otp is None or timezone.now() - otp.created_at > OTP_LIFETIME:
        return False, "That code has expired. Please request a new one."

    if otp.attempts >= MAX_ATTEMPTS:
        otp.used = True
        otp.save(update_fields=["used"])
        return False, "Too many wrong attempts. Please request a new code."

    otp.attempts += 1
    if hmac.compare_digest(otp.code_hash, _hash(code)):
        otp.used = True
        otp.save(update_fields=["attempts", "used"])
        return True, ""

    otp.save(update_fields=["attempts"])
    return False, "That code is not correct."


def send_otp_email(user, code):
    """Email the code. Returns True if it was handed to the mail server."""
    minutes = int(OTP_LIFETIME.total_seconds() // 60)
    message = (
        f"Hello {user.username},\n\n"
        f"Your Saka Keja verification code is: {code}\n\n"
        f"It expires in {minutes} minutes. "
        "If you did not create an account, you can ignore this email.\n"
    )
    try:
        send_mail("Your Saka Keja verification code", message, None, [user.email])
        return True
    except Exception:
        logger.exception("Could not send OTP email to user %s", user.pk)
        return False