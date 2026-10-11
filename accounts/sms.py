"""
SMS sending. Backends (settings.SMS_BACKEND):

  africastalking  real SMS through Africa's Talking (used in production)
  console         development only: prints the message in the runserver terminal
  locmem          tests: keeps messages in sms.outbox

Credentials come from environment variables, never from code.
Nothing here logs the message text, so verification codes never reach the logs.
"""
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

outbox = []  # used by the locmem backend (tests)

# Africa's Talking per-recipient status codes that mean the message was accepted.
ACCEPTED_STATUS_CODES = {100, 101, 102}  # Processed, Sent, Queued


def send_sms(phone, message):
    """Send one SMS. Returns True if the provider accepted it."""
    backend = getattr(settings, "SMS_BACKEND", "africastalking")

    if backend == "locmem":
        outbox.append({"to": phone, "message": message})
        return True

    if backend == "console":
        print(f"\n[DEV SMS to {phone}] {message}\n", flush=True)
        return True

    return _send_africastalking(phone, message)


def _send_africastalking(phone, message):
    username = getattr(settings, "AT_USERNAME", "")
    api_key = getattr(settings, "AT_API_KEY", "")
    if not username or not api_key:
        logger.error("SMS is not configured: set AT_USERNAME and AT_API_KEY.")
        return False

    base_url = getattr(settings, "AT_BASE_URL", "https://api.africastalking.com").rstrip("/")
    fields = {"username": username, "to": phone, "message": message}
    sender_id = getattr(settings, "AT_SENDER_ID", "")
    if sender_id:
        fields["from"] = sender_id

    request = urllib.request.Request(
        f"{base_url}/version1/messaging",
        data=urllib.parse.urlencode(fields).encode(),
        headers={
            "apiKey": api_key,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        logger.error("Africa's Talking rejected the request (HTTP %s).", exc.code)
        return False
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        logger.error("Could not reach Africa's Talking (%s).", type(exc).__name__)
        return False

    recipients = (body.get("SMSMessageData") or {}).get("Recipients") or []
    if recipients and recipients[0].get("statusCode") in ACCEPTED_STATUS_CODES:
        return True

    status = recipients[0].get("status") if recipients else "no recipient in response"
    logger.error("Africa's Talking did not accept the SMS: %s", status)
    return False