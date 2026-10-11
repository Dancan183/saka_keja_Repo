import json
import re
import threading
import time
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts import phone as phone_service
from accounts import sms
from accounts.models import PendingRegistration, PhoneVerification, User

PHONE = "0712345678"
PHONE_E164 = "+254712345678"
OTHER_PHONE = "0798907004"


def email_code():
    return re.search(r"code is: (\d{6})", mail.outbox[-1].body).group(1)


def sms_code():
    return re.search(r"code is (\d{6})\.", sms.outbox[-1]["message"]).group(1)


def wrong(good):
    return "000000" if good != "000000" else "111111"


def post_json(client, name, data, **extra):
    return client.post(reverse(f"accounts:{name}"), json.dumps(data), content_type="application/json", **extra)


def skip_cooldown(client):
    session = client.session
    session.pop(phone_service.LAST_SENT_KEY, None)
    session.save()


@override_settings(SMS_BACKEND="locmem")
class PhoneBase(TestCase):
    def setUp(self):
        sms.outbox.clear()

    def verify_phone(self, client, phone=PHONE):
        skip_cooldown(client)
        sent = post_json(client, "phone_send", {"phone": phone})
        self.assertEqual(sent.status_code, 200, sent.content)
        done = post_json(client, "phone_verify", {"code": sms_code()})
        self.assertEqual(done.status_code, 200, done.content)
        return done


# ---------------------------------------------------------------- phone numbers
class PhoneNumberFormats(TestCase):
    def test_valid_formats_normalise_to_international(self):
        for raw in ["0712345678", "712345678", "+254712345678", "254712345678", "0712 345 678", "0712-345-678", "0112345678"]:
            expected = "+254" + re.sub(r"\D", "", raw)[-9:]
            self.assertEqual(phone_service.normalize_ke_phone(raw), expected, raw)

    def test_invalid_numbers_rejected(self):
        for raw in ["", None, "0612345678", "12345", "07123456789", "+255712345678", "abc", "071234567", "+2547123456789"]:
            self.assertIsNone(phone_service.normalize_ke_phone(raw), raw)


# ---------------------------------------------------------------- send / verify API
class PhoneVerificationAPI(PhoneBase):
    def test_empty_phone_number(self):
        r = post_json(self.client, "phone_send", {"phone": "  "})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["message"], "Enter your phone number first.")
        self.assertEqual(len(sms.outbox), 0)

    def test_invalid_phone_number(self):
        r = post_json(self.client, "phone_send", {"phone": "12345"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("valid Kenyan", r.json()["message"])
        self.assertEqual(len(sms.outbox), 0)

    def test_send_succeeds_and_never_exposes_the_code(self):
        r = post_json(self.client, "phone_send", {"phone": "0712 345 678"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["message"], "Verification code sent successfully.")
        self.assertEqual(len(sms.outbox), 1)
        self.assertEqual(sms.outbox[0]["to"], PHONE_E164)
        code = sms_code()
        self.assertNotIn(code, r.content.decode())              # not in the API response
        row = PhoneVerification.objects.get()
        self.assertEqual(len(row.code_hash), 64)                # only a hash is stored
        self.assertNotIn(code, row.code_hash)
        self.assertEqual(row.phone, PHONE_E164)
        self.assertTrue(row.sent_ok)

    def test_code_is_six_digits_and_random(self):
        codes = set()
        for _ in range(8):
            skip_cooldown(self.client)
            PhoneVerification.objects.all().delete()
            post_json(self.client, "phone_send", {"phone": PHONE})
            codes.add(sms_code())
        self.assertTrue(all(len(c) == 6 and c.isdigit() for c in codes))
        self.assertGreater(len(codes), 1)

    def test_cooldown_between_sends(self):
        post_json(self.client, "phone_send", {"phone": PHONE})
        r = post_json(self.client, "phone_send", {"phone": PHONE})
        self.assertEqual(r.status_code, 429)
        self.assertGreater(r.json()["retry_after"], 0)
        self.assertEqual(len(sms.outbox), 1)

    def test_per_phone_hourly_limit(self):
        for i in range(phone_service.MAX_SENDS_PER_PHONE_PER_HOUR):
            PhoneVerification.objects.create(token=f"t{i}", phone=PHONE_E164, code_hash="x")
        r = post_json(self.client, "phone_send", {"phone": PHONE})
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.json()["code"], "phone_limit")
        self.assertEqual(len(sms.outbox), 0)

    def test_per_ip_hourly_limit(self):
        for i in range(phone_service.MAX_SENDS_PER_IP_PER_HOUR):
            PhoneVerification.objects.create(token=f"i{i}", phone=f"+25471000000{i}", code_hash="x", ip_address="10.1.1.1")
        r = post_json(self.client, "phone_send", {"phone": PHONE}, HTTP_X_FORWARDED_FOR="10.1.1.1")
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.json()["code"], "ip_limit")

    def test_correct_code_verifies(self):
        post_json(self.client, "phone_send", {"phone": PHONE})
        r = post_json(self.client, "phone_verify", {"code": sms_code()})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["phone"], PHONE_E164)
        self.assertIsNotNone(PhoneVerification.objects.get().verified_at)

    def test_wrong_code_then_lockout_after_five(self):
        post_json(self.client, "phone_send", {"phone": PHONE})
        good = sms_code()
        for left in (4, 3, 2, 1, 0):
            r = post_json(self.client, "phone_verify", {"code": wrong(good)})
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.json()["attempts_left"], left)
        r = post_json(self.client, "phone_verify", {"code": good})        # even the right code is refused now
        self.assertEqual(r.status_code, 429)
        self.assertEqual(r.json()["code"], "locked")
        self.assertIsNone(PhoneVerification.objects.get().verified_at)

    def test_code_expires_after_five_minutes(self):
        post_json(self.client, "phone_send", {"phone": PHONE})
        PhoneVerification.objects.update(created_at=timezone.now() - timedelta(minutes=6))
        r = post_json(self.client, "phone_verify", {"code": sms_code()})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["code"], "expired")

    def test_code_is_bound_to_its_phone_number(self):
        post_json(self.client, "phone_send", {"phone": PHONE})
        good = sms_code()
        PhoneVerification.objects.update(phone="+254798907004")       # someone swaps the number in the database
        r = post_json(self.client, "phone_verify", {"code": good})
        self.assertEqual(r.json()["code"], "wrong_code")

    def test_verify_without_requesting_a_code(self):
        r = post_json(self.client, "phone_verify", {"code": "123456"})
        self.assertEqual(r.json()["code"], "no_code")

    def test_code_must_be_six_digits(self):
        post_json(self.client, "phone_send", {"phone": PHONE})
        for bad in ["12345", "1234567", "abcdef", ""]:
            self.assertEqual(post_json(self.client, "phone_verify", {"code": bad}).json()["code"], "bad_format")

    def test_other_browser_cannot_use_my_code(self):
        post_json(self.client, "phone_send", {"phone": PHONE})
        other = Client()
        r = post_json(other, "phone_verify", {"code": sms_code()})
        self.assertEqual(r.json()["code"], "no_code")

    def test_reset_invalidates_the_code(self):
        post_json(self.client, "phone_send", {"phone": PHONE})
        good = sms_code()
        self.assertEqual(post_json(self.client, "phone_reset", {}).status_code, 200)
        self.assertEqual(PhoneVerification.objects.count(), 0)
        self.assertEqual(post_json(self.client, "phone_verify", {"code": good}).json()["code"], "no_code")

    def test_reset_does_not_skip_the_send_cooldown(self):
        post_json(self.client, "phone_send", {"phone": PHONE})
        post_json(self.client, "phone_reset", {})
        r = post_json(self.client, "phone_send", {"phone": OTHER_PHONE})
        self.assertEqual(r.status_code, 429)

    def test_provider_failure_is_reported_gracefully(self):
        with mock.patch("accounts.sms.send_sms", return_value=False):
            r = post_json(self.client, "phone_send", {"phone": PHONE})
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json()["message"], "Failed to send code. Please try again.")
        self.assertNotIn(phone_service.SESSION_KEY, self.client.session)
        # a failed send must not block an immediate retry
        self.assertEqual(post_json(self.client, "phone_send", {"phone": PHONE}).status_code, 200)

    @override_settings(SMS_BACKEND="africastalking", AT_USERNAME="", AT_API_KEY="")
    def test_unconfigured_provider_fails_cleanly(self):
        with self.assertLogs("accounts.sms", level="ERROR"):
            r = post_json(self.client, "phone_send", {"phone": PHONE})
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json()["message"], "Failed to send code. Please try again.")

    def test_endpoints_need_post_and_csrf(self):
        for name in ["phone_send", "phone_verify", "phone_reset"]:
            self.assertEqual(self.client.get(reverse(f"accounts:{name}")).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        r = strict.post(reverse("accounts:phone_send"), json.dumps({"phone": PHONE}), content_type="application/json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(len(sms.outbox), 0)

    def test_new_number_replaces_old_verification(self):
        self.verify_phone(self.client, PHONE)
        self.verify_phone(self.client, OTHER_PHONE)
        self.assertEqual(PhoneVerification.objects.count(), 1)
        self.assertEqual(phone_service.verified_phone(self.client_request()), "+254798907004")

    def client_request(self):
        class R:  # a minimal stand-in carrying this client's session
            session = self.client.session
        return R()


# ---------------------------------------------------------------- Africa's Talking client
class FakeATServer:
    """A tiny local HTTP server that behaves like the Africa's Talking messaging endpoint."""

    def __init__(self, status=200, body=None):
        self.requests = []
        outer = self
        self.status = status
        self.body = body if body is not None else {
            "SMSMessageData": {"Message": "Sent to 1/1 Total Cost: KES 0.8000",
                               "Recipients": [{"statusCode": 102, "number": PHONE_E164, "status": "Success", "cost": "KES 0.8000"}]}
        }

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                outer.requests.append({"path": self.path, "headers": dict(self.headers), "body": self.rfile.read(length).decode()})
                payload = json.dumps(outer.body) if isinstance(outer.body, dict) else outer.body
                self.send_response(outer.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload.encode())

            def log_message(self, *args):
                pass

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class AfricasTalkingBackend(TestCase):
    def run_with(self, server, **overrides):
        settings_kwargs = dict(SMS_BACKEND="africastalking", AT_USERNAME="sandbox", AT_API_KEY="secret-key-123",
                               AT_BASE_URL=server.url, AT_SENDER_ID="")
        settings_kwargs.update(overrides)
        with override_settings(**settings_kwargs):
            return sms.send_sms(PHONE_E164, "Your Saka Keja verification code is 482913. It expires in 5 minutes.")

    def test_request_matches_the_provider_format(self):
        server = FakeATServer()
        self.addCleanup(server.close)
        self.assertTrue(self.run_with(server, AT_SENDER_ID="SAKAKEJA"))
        sent = server.requests[0]
        self.assertEqual(sent["path"], "/version1/messaging")
        headers = {k.lower(): v for k, v in sent["headers"].items()}      # header names are case-insensitive
        self.assertEqual(headers["apikey"], "secret-key-123")            # key goes in a header, not the body
        self.assertEqual(headers["accept"], "application/json")
        self.assertNotIn("secret-key-123", sent["body"])
        self.assertIn("username=sandbox", sent["body"])
        self.assertIn("to=%2B254712345678", sent["body"])
        self.assertIn("from=SAKAKEJA", sent["body"])
        self.assertIn("482913", sent["body"])

    def test_accepted_status_codes(self):
        for code in (100, 101, 102):
            server = FakeATServer(body={"SMSMessageData": {"Recipients": [{"statusCode": code, "status": "Success"}]}})
            self.addCleanup(server.close)
            self.assertTrue(self.run_with(server), code)

    def test_rejected_by_provider(self):
        for code in (403, 405, 406, 500):
            server = FakeATServer(body={"SMSMessageData": {"Recipients": [{"statusCode": code, "status": "Failed"}]}})
            self.addCleanup(server.close)
            with self.assertLogs("accounts.sms", level="ERROR"):
                self.assertFalse(self.run_with(server), code)

    def test_http_error_bad_json_and_no_recipients(self):
        for status, body in [(401, {"error": "bad key"}), (200, "not json"), (200, {"SMSMessageData": {"Recipients": []}})]:
            server = FakeATServer(status=status, body=body)
            self.addCleanup(server.close)
            with self.assertLogs("accounts.sms", level="ERROR"):
                self.assertFalse(self.run_with(server), (status, body))

    def test_unreachable_provider(self):
        server = FakeATServer()
        url = server.url
        server.close()
        with self.assertLogs("accounts.sms", level="ERROR"):
            with override_settings(SMS_BACKEND="africastalking", AT_USERNAME="u", AT_API_KEY="k", AT_BASE_URL=url):
                self.assertFalse(sms.send_sms(PHONE_E164, "x"))

    def test_logs_never_contain_the_code_or_the_key(self):
        server = FakeATServer(body={"SMSMessageData": {"Recipients": [{"statusCode": 403, "status": "InvalidPhoneNumber"}]}})
        self.addCleanup(server.close)
        with self.assertLogs("accounts.sms", level="ERROR") as logs:
            self.run_with(server)
        text = "\n".join(logs.output)
        self.assertNotIn("482913", text)
        self.assertNotIn("secret-key-123", text)


# ---------------------------------------------------------------- registration is blocked until verified
class RegistrationRequiresVerifiedPhone(PhoneBase):
    PASSWORD = "S3cure-pass-99"

    def register(self, client=None, role="tenant", verify=True, phone=PHONE, **extra):
        client = client or self.client
        if verify:
            self.verify_phone(client, phone)
        data = {"username": "dan", "email": "Dan@Example.com", "phone_number": phone, "role": role,
                "password1": self.PASSWORD, "password2": self.PASSWORD}
        data.update(extra)
        return client.post(reverse("accounts:register"), data)

    def test_register_page_has_locked_code_field_and_buttons(self):
        html = self.client.get(reverse("accounts:register")).content.decode()
        self.assertRegex(html, r'<input[^>]*id="id_phone_code"[^>]*\bdisabled\b')
        self.assertRegex(html, r'<button[^>]*id="phone-verify"[^>]*\bdisabled\b')
        self.assertIn("Confirm Phone Number", html)
        self.assertIn("Verify Code", html)
        self.assertIn("phone_verify.js", html)
        for kept in ["id_username", "id_email", "id_role", "id_password1", "id_password2"]:
            self.assertIn(kept, html)
        self.assertNotIn('name="phone_code"', html)           # the code is never part of the posted form

    def test_rejected_when_phone_was_never_verified(self):
        r = self.register(verify=False)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "verify this phone number first")
        self.assertEqual(PendingRegistration.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_rejected_when_code_sent_but_not_entered(self):
        post_json(self.client, "phone_send", {"phone": PHONE})
        r = self.register(verify=False)
        self.assertContains(r, "verify this phone number first")
        self.assertEqual(PendingRegistration.objects.count(), 0)

    def test_rejected_for_a_different_number_than_the_verified_one(self):
        self.verify_phone(self.client, PHONE)
        r = self.register(verify=False, phone=OTHER_PHONE)
        self.assertContains(r, "verify this phone number first")
        self.assertEqual(PendingRegistration.objects.count(), 0)

    def test_same_number_in_another_format_is_accepted(self):
        self.verify_phone(self.client, PHONE)
        r = self.register(verify=False, phone="+254 712 345 678")
        self.assertRedirects(r, reverse("accounts:verify_email"))

    def test_changing_the_number_revokes_verification(self):
        self.verify_phone(self.client, PHONE)
        post_json(self.client, "phone_reset", {})              # what the page does when the number is edited
        r = self.register(verify=False)
        self.assertContains(r, "verify this phone number first")

    def test_verification_cannot_be_used_from_another_browser(self):
        self.verify_phone(self.client, PHONE)
        r = self.register(client=Client(), verify=False)
        self.assertContains(r, "verify this phone number first")
        self.assertEqual(PendingRegistration.objects.count(), 0)

    def test_unverified_registration_cannot_skip_the_check_with_extra_fields(self):
        r = self.register(verify=False, phone_verified="true", is_verified="1")
        self.assertContains(r, "verify this phone number first")

    def test_blank_or_invalid_phone_rejected_by_the_form(self):
        for bad, text in [("", "required"), ("12345", "valid Kenyan")]:
            r = self.register(verify=False, phone=bad)
            self.assertContains(r, text)
        self.assertEqual(PendingRegistration.objects.count(), 0)

    def test_full_flow_creates_account_with_international_phone_and_consumes_verification(self):
        r = self.register()
        self.assertRedirects(r, reverse("accounts:verify_email"))
        self.assertEqual(User.objects.count(), 0)
        pending = PendingRegistration.objects.get()
        self.assertEqual(pending.phone_number, PHONE_E164)
        self.assertEqual(pending.phone_token, PhoneVerification.objects.get().token)

        done = self.client.post(reverse("accounts:verify_email"), {"code": email_code()})
        self.assertRedirects(done, reverse("properties:house_list"), fetch_redirect_response=False)
        user = User.objects.get()
        self.assertEqual(user.phone_number, PHONE_E164)
        self.assertTrue(user.check_password(self.PASSWORD))
        self.assertIsNotNone(PhoneVerification.objects.get().consumed_at)

    def test_verification_is_single_use(self):
        self.register()
        self.client.post(reverse("accounts:verify_email"), {"code": email_code()})
        self.client.post(reverse("accounts:logout"))
        r = self.register(verify=False, username="dan2", email="two@example.com")
        self.assertContains(r, "verify this phone number first")
        self.assertEqual(User.objects.count(), 1)

    def test_phone_check_is_enforced_again_when_the_account_is_created(self):
        self.register()
        PhoneVerification.objects.update(verified_at=timezone.now() - timedelta(minutes=61))
        r = self.client.post(reverse("accounts:verify_email"), {"code": email_code()})
        self.assertRedirects(r, reverse("accounts:register"), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(PendingRegistration.objects.count(), 0)

    def test_pending_signup_without_phone_proof_cannot_become_an_account(self):
        self.register()
        PendingRegistration.objects.update(phone_token="")     # tampering / legacy row
        r = self.client.post(reverse("accounts:verify_email"), {"code": email_code()})
        self.assertRedirects(r, reverse("accounts:register"), fetch_redirect_response=False)
        self.assertEqual(User.objects.count(), 0)

    def test_reloaded_form_keeps_verified_state(self):
        self.verify_phone(self.client, PHONE)
        r = self.register(verify=False, password2="different-Pass-1")       # fails on the password
        self.assertContains(r, 'data-verified="true"')
        r = self.register(verify=False, phone=OTHER_PHONE, password2="different-Pass-1")
        self.assertContains(r, 'data-verified="false"')


# ---------------------------------------------------------------- email code step (unchanged behaviour)
class EmailCodeStep(PhoneBase):
    PASSWORD = "S3cure-pass-99"

    def register(self, client=None, role="tenant", **extra):
        client = client or self.client
        self.verify_phone(client)
        data = {"username": "dan", "email": "Dan@Example.com", "phone_number": PHONE, "role": role,
                "password1": self.PASSWORD, "password2": self.PASSWORD}
        data.update(extra)
        return client.post(reverse("accounts:register"), data)

    def verify(self, code, client=None):
        return (client or self.client).post(reverse("accounts:verify_email"), {"code": code})

    def age_pending(self, **kwargs):
        PendingRegistration.objects.update(**{k: timezone.now() - v for k, v in kwargs.items()})

    def test_no_user_row_until_email_verified(self):
        self.assertRedirects(self.register(), reverse("accounts:verify_email"))
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["dan@example.com"])

    def test_pending_row_never_stores_plain_password_or_code(self):
        self.register()
        p = PendingRegistration.objects.get()
        self.assertNotIn(self.PASSWORD, p.password_hash)
        self.assertEqual(len(p.code_hash), 64)
        self.assertNotIn(email_code(), p.code_hash)

    def test_correct_code_creates_active_user(self):
        self.register()
        r = self.verify(email_code())
        self.assertRedirects(r, reverse("properties:house_list"), fetch_redirect_response=False)
        u = User.objects.get()
        self.assertTrue(u.is_active)
        self.assertEqual((u.username, u.email, u.role, u.phone_number), ("dan", "dan@example.com", "tenant", PHONE_E164))
        self.assertEqual(PendingRegistration.objects.count(), 0)
        self.assertIn("_auth_user_id", self.client.session)

    def test_landlord_goes_to_add_house(self):
        self.register(role="landlord")
        r = self.verify(email_code())
        self.assertRedirects(r, reverse("properties:house_create"), fetch_redirect_response=False)
        self.assertTrue(User.objects.get().is_landlord)

    def test_wrong_code_locks_after_five(self):
        self.register()
        good = email_code()
        for _ in range(5):
            self.assertContains(self.verify(wrong(good)), "not correct")
        self.assertContains(self.verify(good), "Too many wrong attempts")
        self.assertEqual(User.objects.count(), 0)

    def test_code_expires(self):
        self.register()
        good = email_code()
        self.age_pending(code_sent_at=timedelta(minutes=11))
        self.assertContains(self.verify(good), "expired")

    def test_whole_signup_expires_and_is_purged(self):
        self.register()
        self.age_pending(created_at=timedelta(minutes=31), code_sent_at=timedelta(minutes=1))
        self.assertRedirects(self.client.get(reverse("accounts:verify_email")), reverse("accounts:register"))
        self.assertEqual(PendingRegistration.objects.count(), 0)

    def test_other_browser_cannot_finish_my_signup(self):
        self.register()
        self.assertRedirects(self.verify(email_code(), Client()), reverse("accounts:register"))
        self.assertEqual(User.objects.count(), 0)

    def test_overwriting_someone_elses_pending_signup_is_blocked(self):
        victim, attacker = Client(), Client()
        self.register(client=victim, username="victim")
        victim_code = email_code()
        r = self.register(client=attacker, username="evil", password1="Evil-pass-12345", password2="Evil-pass-12345")
        self.assertContains(r, "wait a minute")
        self.age_pending(code_sent_at=timedelta(minutes=2))
        self.register(client=attacker, username="evil", password1="Evil-pass-12345", password2="Evil-pass-12345")
        self.assertRedirects(self.verify(victim_code, victim), reverse("accounts:register"))
        self.assertEqual(User.objects.count(), 0)

    def test_resend_cooldown_then_new_code(self):
        self.register()
        self.client.post(reverse("accounts:resend_code"))
        self.assertEqual(len(mail.outbox), 1)
        self.age_pending(code_sent_at=timedelta(minutes=2))
        self.client.post(reverse("accounts:resend_code"))
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(self.verify(email_code()).status_code, 302)

    def test_registered_email_rejected_up_front(self):
        User.objects.create_user("old", "dan@example.com", "pw-12345-abcd")
        self.verify_phone(self.client)
        data = {"username": "dan", "email": "dan@example.com", "phone_number": PHONE, "role": "tenant",
                "password1": self.PASSWORD, "password2": self.PASSWORD}
        self.assertContains(self.client.post(reverse("accounts:register"), data), "already exists")
        self.assertEqual(PendingRegistration.objects.count(), 0)

    def test_username_taken_while_waiting_fails_cleanly(self):
        self.register()
        good = email_code()
        User.objects.create_user("dan", "someone@else.com", "pw-12345-abcd")
        self.assertRedirects(self.verify(good), reverse("accounts:register"))
        self.assertEqual(PendingRegistration.objects.count(), 0)
        # the phone verification was NOT consumed by the failed attempt
        self.assertIsNone(PhoneVerification.objects.get().consumed_at)

    def test_email_failure_does_not_create_user(self):
        with mock.patch("accounts.otp.send_mail", side_effect=OSError("smtp down")), \
                self.assertLogs("accounts.otp", level="ERROR"):
            r = self.register()
        self.assertRedirects(r, reverse("accounts:verify_email"))
        self.assertEqual(User.objects.count(), 0)

    @override_settings(EMAIL_IS_CONFIGURED=False)
    def test_unconfigured_email_in_production_reports_failure(self):
        with self.assertLogs("accounts.otp", level="ERROR"):
            r = self.register()
        self.assertRedirects(r, reverse("accounts:verify_email"), fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse("accounts:verify_email")), "could not send the email")
        self.assertEqual(User.objects.count(), 0)

    def test_masked_email_shown(self):
        self.register()
        page = self.client.get(reverse("accounts:verify_email"))
        self.assertContains(page, "d***@example.com")
        self.assertNotContains(page, "dan@example.com")

    @override_settings(AUTH_PASSWORD_VALIDATORS=[
        {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
        {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    ])
    def test_weak_or_mismatched_password_creates_nothing(self):
        for p1, p2 in [("12345678", "12345678"), (self.PASSWORD, "different-Pass-1")]:
            self.assertEqual(self.register(password1=p1, password2=p2).status_code, 200)
        self.assertEqual(PendingRegistration.objects.count(), 0)

    def test_pages_render(self):
        for name in ["login", "register", "password_reset", "password_reset_done", "password_reset_complete"]:
            self.assertEqual(self.client.get(reverse(f"accounts:{name}")).status_code, 200, name)


class PasswordReset(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("sam", "sam@example.com", "Old-pass-12345")

    def test_full_reset_flow(self):
        r = self.client.post(reverse("accounts:password_reset"), {"email": "sam@example.com"})
        self.assertRedirects(r, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        link = re.search(r"http://\S+/accounts/password-reset/\S+/\S+/", mail.outbox[0].body).group(0)
        path = link.split("testserver")[1]
        r = self.client.get(path, follow=True)
        self.assertContains(r, "Choose a new password")
        post_url = r.redirect_chain[-1][0]
        r = self.client.post(post_url, {"new_password1": "Brand-new-pass-77", "new_password2": "Brand-new-pass-77"})
        self.assertRedirects(r, reverse("accounts:password_reset_complete"))
        self.assertTrue(self.client.login(username="sam", password="Brand-new-pass-77"))
        self.assertContains(self.client.get(path, follow=True), "isn't valid")

    def test_unknown_email_same_response_no_mail(self):
        r = self.client.post(reverse("accounts:password_reset"), {"email": "ghost@example.com"})
        self.assertRedirects(r, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)