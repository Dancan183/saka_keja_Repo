"""
Phone number verification by SMS.

Rules enforced here (on the server, never only in the browser):
  * one random 6-digit code, valid 5 minutes, only a hash is stored;
  * the hash covers the phone number, so a code works for that number only;
  * 5 wrong tries per code, 60 s between sends, 5 codes per number per hour,
    10 codes per IP address per hour;
  * the verified state belongs to one browser session and one phone number,
    and is consumed when the account is created.
"""
import hashlib
import hmac
import ipaddress
import logging
import re
import secrets
import time
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from . import sms
from .models import PhoneVerification

logger = logging.getLogger(__name__)

SESSION_KEY = "phone_verification_token"
LAST_SENT_KEY = "phone_last_sent_at"

CODE_LENGTH = 6
CODE_LIFETIME = timedelta(minutes=5)
VERIFIED_LIFETIME = timedelta(minutes=60)  # time allowed to finish registering after verifying
SEND_COOLDOWN_SECONDS = 60
MAX_ATTEMPTS = 5
MAX_SENDS_PER_PHONE_PER_HOUR = 5
MAX_SENDS_PER_IP_PER_HOUR = 10

_KE_PHONE = re.compile(r"^(?:\+?254|0)?([17]\d{8})$")


class PhoneError(Exception):
    def __init__(self, code, message, status=400, **extra):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.extra = extra


def normalize_ke_phone(raw):
    """'0712 345 678', '+254712345678', '254712345678' -> '+254712345678'. None if invalid."""
    if not raw:
        return None
    cleaned = re.sub(r"[\s\-().]", "", str(raw))
    match = _KE_PHONE.match(cleaned)
    return f"+254{match.group(1)}" if match else None


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    candidate = forwarded.split(",")[0].strip() if forwarded else request.META.get("REMOTE_ADDR", "")
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


def _hash(phone, code):
    message = f"{phone}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def _purge_old():
    PhoneVerification.objects.filter(created_at__lt=timezone.now() - timedelta(hours=24)).delete()


def _current_row(request):
    token = request.session.get(SESSION_KEY)
    if not token:
        return None
    return PhoneVerification.objects.filter(token=token, consumed_at__isnull=True).first()


def verified_row_for(token, phone):
    """The verified, unused, unexpired verification for exactly this token and phone."""
    if not token or not phone:
        return None
    return PhoneVerification.objects.filter(
        token=token,
        phone=phone,
        verified_at__isnull=False,
        consumed_at__isnull=True,
        verified_at__gt=timezone.now() - VERIFIED_LIFETIME,
    ).first()


def verified_phone(request):
    """The phone number this browser has verified (and not yet used), or None."""
    row = _current_row(request)
    if row and row.verified_at and timezone.now() - row.verified_at < VERIFIED_LIFETIME:
        return row.phone
    return None


def send_code(request, raw_phone):
    phone = normalize_ke_phone(raw_phone)
    if not phone:
        raise PhoneError("invalid_phone", "Enter a valid Kenyan phone number, for example 0712 345 678.")

    _purge_old()
    now = timezone.now()

    # 1. Wait between sends (kept in the session so resetting the form does not skip it).
    elapsed = time.time() - request.session.get(LAST_SENT_KEY, 0)
    if elapsed < SEND_COOLDOWN_SECONDS:
        wait = int(SEND_COOLDOWN_SECONDS - elapsed) + 1
        raise PhoneError("cooldown", f"Please wait {wait} seconds before requesting another code.", 429, retry_after=wait)

    # 2. Hourly limits per number and per IP address.
    hour_ago = now - timedelta(hours=1)
    if PhoneVerification.objects.filter(phone=phone, created_at__gt=hour_ago).count() >= MAX_SENDS_PER_PHONE_PER_HOUR:
        raise PhoneError("phone_limit", "Too many codes were requested for this number. Please try again later.", 429)
    ip = client_ip(request)
    if ip and PhoneVerification.objects.filter(ip_address=ip, created_at__gt=hour_ago).count() >= MAX_SENDS_PER_IP_PER_HOUR:
        raise PhoneError("ip_limit", "Too many requests from your network. Please try again later.", 429)

    code = f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"
    row = PhoneVerification.objects.create(
        token=secrets.token_urlsafe(32),
        phone=phone,
        code_hash=_hash(phone, code),
        ip_address=ip,
        created_at=now,
    )

    if not sms.send_sms(phone, f"Your Saka Keja verification code is {code}. It expires in 5 minutes. Do not share it."):
        raise PhoneError("send_failed", "Failed to send code. Please try again.", 502)

    row.sent_ok = True
    row.save(update_fields=["sent_ok"])

    # The new code replaces whatever this browser had before.
    old_token = request.session.get(SESSION_KEY)
    if old_token:
        PhoneVerification.objects.filter(token=old_token, consumed_at__isnull=True).delete()
    request.session[SESSION_KEY] = row.token
    request.session[LAST_SENT_KEY] = time.time()

    return {
        "ok": True,
        "message": "Verification code sent successfully.",
        "cooldown": SEND_COOLDOWN_SECONDS,
        "expires_in": int(CODE_LIFETIME.total_seconds()),
    }


def verify_code(request, raw_code):
    code = (raw_code or "").strip()
    if not (code.isdigit() and len(code) == CODE_LENGTH):
        raise PhoneError("bad_format", "Enter the 6-digit code.")

    token = request.session.get(SESSION_KEY)
    with transaction.atomic():
        row = (
            PhoneVerification.objects.select_for_update()
            .filter(token=token or "", consumed_at__isnull=True, sent_ok=True)
            .first()
        )
        if row is None:
            raise PhoneError("no_code", "Request a verification code first.")

        if row.verified_at:
            return {"ok": True, "message": "Phone number verified.", "phone": row.phone}

        if timezone.now() - row.created_at > CODE_LIFETIME:
            raise PhoneError("expired", "That code has expired. Please request a new one.")
        if row.attempts >= MAX_ATTEMPTS:
            raise PhoneError("locked", "Too many wrong attempts. Please request a new code.", 429)

        row.attempts += 1
        if hmac.compare_digest(row.code_hash, _hash(row.phone, code)):
            row.verified_at = timezone.now()
            row.save(update_fields=["attempts", "verified_at"])
            return {"ok": True, "message": "Phone number verified successfully.", "phone": row.phone}

        row.save(update_fields=["attempts"])
        left = MAX_ATTEMPTS - row.attempts

    # Raised AFTER the transaction has committed. Raising inside it would roll the
    # attempt counter back and allow unlimited guesses.
    hint = f" {left} attempt{'s' if left != 1 else ''} left." if left else ""
    raise PhoneError("wrong_code", f"That code is not correct.{hint}", 400, attempts_left=left)


def reset(request):
    """Forget this browser's verification (used when the phone number is edited)."""
    token = request.session.pop(SESSION_KEY, None)
    if token:
        PhoneVerification.objects.filter(token=token, consumed_at__isnull=True).delete()
    return {"ok": True}