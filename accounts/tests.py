import re
from datetime import timedelta

from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import PendingRegistration, User


def code_from_outbox():
    return re.search(r"code is: (\d{6})", mail.outbox[-1].body).group(1)


def wrong_code(good):
    return "000000" if good != "000000" else "111111"


class SignUpOnlyAfterVerification(TestCase):
    PASSWORD = "S3cure-pass-99"

    def register(self, client=None, role="tenant", **extra):
        data = {
            "username": "dan", "email": "Dan@Example.com", "phone_number": "0798907004",
            "role": role, "password1": self.PASSWORD, "password2": self.PASSWORD,
        }
        data.update(extra)
        return (client or self.client).post(reverse("accounts:register"), data)

    def verify(self, code, client=None):
        return (client or self.client).post(reverse("accounts:verify_email"), {"code": code})

    def age_pending(self, **kwargs):
        PendingRegistration.objects.update(**{k: timezone.now() - v for k, v in kwargs.items()})

    # ---- the core rule ----
    def test_no_user_row_until_verified(self):
        r = self.register()
        self.assertRedirects(r, reverse("accounts:verify_email"))
        self.assertEqual(User.objects.count(), 0)               # nothing in the users table
        self.assertEqual(PendingRegistration.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["dan@example.com"])

    def test_pending_row_never_stores_plain_password_or_code(self):
        self.register()
        p = PendingRegistration.objects.get()
        self.assertNotIn(self.PASSWORD, p.password_hash)
        self.assertTrue(p.password_hash.startswith(("pbkdf2_", "argon2", "bcrypt", "scrypt")))
        self.assertEqual(len(p.code_hash), 64)
        self.assertNotIn(code_from_outbox(), p.code_hash)

    def test_correct_code_creates_active_user_and_removes_pending(self):
        self.register()
        r = self.verify(code_from_outbox())
        self.assertRedirects(r, reverse("properties:house_list"), fetch_redirect_response=False)
        u = User.objects.get()
        self.assertTrue(u.is_active)
        self.assertEqual((u.username, u.email, u.role, u.phone_number), ("dan", "dan@example.com", "tenant", "0798907004"))
        self.assertTrue(u.check_password(self.PASSWORD))         # hashed password carried over correctly
        self.assertEqual(PendingRegistration.objects.count(), 0)
        self.assertIn("_auth_user_id", self.client.session)

    def test_landlord_goes_to_add_house(self):
        self.register(role="landlord")
        r = self.verify(code_from_outbox())
        self.assertRedirects(r, reverse("properties:house_create"), fetch_redirect_response=False)
        self.assertTrue(User.objects.get().is_landlord)

    def test_can_log_in_after_verifying_not_before(self):
        self.register()
        c2 = Client()
        self.assertFalse(c2.login(username="dan", password=self.PASSWORD))   # no account yet
        self.verify(code_from_outbox())
        self.assertTrue(Client().login(username="dan", password=self.PASSWORD))

    # ---- wrong, expired, reused ----
    def test_wrong_code_creates_nothing_and_locks_after_5(self):
        self.register()
        good = code_from_outbox()
        for _ in range(5):
            self.assertContains(self.verify(wrong_code(good)), "not correct")
        self.assertContains(self.verify(good), "Too many wrong attempts")
        self.assertEqual(User.objects.count(), 0)

    def test_code_expires_after_10_minutes(self):
        self.register()
        good = code_from_outbox()
        self.age_pending(code_sent_at=timedelta(minutes=11))
        self.assertContains(self.verify(good), "expired")
        self.assertEqual(User.objects.count(), 0)

    def test_whole_signup_expires_after_30_minutes_and_is_purged(self):
        self.register()
        self.age_pending(created_at=timedelta(minutes=31), code_sent_at=timedelta(minutes=1))
        r = self.client.get(reverse("accounts:verify_email"))
        self.assertRedirects(r, reverse("accounts:register"))
        self.assertEqual(PendingRegistration.objects.count(), 0)

    def test_code_cannot_be_used_twice(self):
        self.register()
        good = code_from_outbox()
        self.verify(good)
        c2 = Client()  # someone replaying the code without the session
        self.assertRedirects(self.verify(good, c2), reverse("accounts:register"))
        self.assertEqual(User.objects.count(), 1)

    # ---- session binding ----
    def test_verify_without_started_signup_redirects_to_register(self):
        self.assertRedirects(self.client.get(reverse("accounts:verify_email")), reverse("accounts:register"))
        self.assertRedirects(self.verify("123456"), reverse("accounts:register"))
        self.assertEqual(User.objects.count(), 0)

    def test_other_browser_cannot_finish_my_signup(self):
        self.register()
        good = code_from_outbox()
        attacker = Client()
        self.assertRedirects(self.verify(good, attacker), reverse("accounts:register"))
        self.assertEqual(User.objects.count(), 0)

    def test_overwriting_someone_elses_pending_signup_is_blocked_then_harmless(self):
        victim = Client()
        self.register(client=victim, username="victim")
        victim_code = code_from_outbox()
        attacker = Client()
        # within the cooldown the attacker cannot overwrite or re-send
        r = self.register(client=attacker, username="evil", password1="Evil-pass-12345", password2="Evil-pass-12345")
        self.assertContains(r, "wait a minute")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(PendingRegistration.objects.get().username, "victim")
        # after the cooldown the attacker can overwrite, but the victim's browser can no longer finish it
        self.age_pending(code_sent_at=timedelta(minutes=2))
        self.register(client=attacker, username="evil", password1="Evil-pass-12345", password2="Evil-pass-12345")
        self.assertRedirects(self.verify(victim_code, victim), reverse("accounts:register"))
        self.assertEqual(User.objects.count(), 0)

    # ---- resend ----
    def test_resend_cooldown_then_new_code_replaces_old(self):
        self.register()
        old = code_from_outbox()
        self.client.post(reverse("accounts:resend_code"))
        self.assertEqual(len(mail.outbox), 1)                   # blocked by cooldown
        self.age_pending(code_sent_at=timedelta(minutes=2))
        self.client.post(reverse("accounts:resend_code"))
        self.assertEqual(len(mail.outbox), 2)
        new = code_from_outbox()
        if new != old:
            self.assertContains(self.verify(old), "not correct")
        self.assertEqual(self.verify(new).status_code, 302)
        self.assertEqual(User.objects.count(), 1)

    def test_resend_without_signup_redirects(self):
        self.assertRedirects(self.client.post(reverse("accounts:resend_code")), reverse("accounts:register"))
        self.assertEqual(len(mail.outbox), 0)

    # ---- validation and races ----
    def test_registered_email_is_rejected_up_front(self):
        User.objects.create_user("old", "dan@example.com", "pw-12345-abcd")
        r = self.register()
        self.assertContains(r, "already exists")
        self.assertEqual(PendingRegistration.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_username_taken_while_waiting_fails_cleanly(self):
        self.register()
        good = code_from_outbox()
        User.objects.create_user("dan", "someone@else.com", "pw-12345-abcd")  # takes the username meanwhile
        r = self.verify(good)
        self.assertRedirects(r, reverse("accounts:register"))
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(PendingRegistration.objects.count(), 0)

    def test_landlord_requires_phone(self):
        r = self.register(role="landlord", phone_number="")
        self.assertContains(r, "must provide a phone number")
        self.assertEqual(PendingRegistration.objects.count(), 0)

    @override_settings(AUTH_PASSWORD_VALIDATORS=[
        {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
        {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    ])
    def test_weak_or_mismatched_password_creates_nothing(self):
        for p1, p2 in [("12345678", "12345678"), (self.PASSWORD, "different-Pass-1")]:
            r = self.register(password1=p1, password2=p2)
            self.assertEqual(r.status_code, 200)
        self.assertEqual(PendingRegistration.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_failure_does_not_create_user(self):
        from unittest import mock
        with mock.patch("accounts.otp.send_mail", side_effect=OSError("smtp down")), \
                self.assertLogs("accounts.otp", level="ERROR"):
            r = self.register()
        self.assertRedirects(r, reverse("accounts:verify_email"))
        self.assertEqual(User.objects.count(), 0)

    def test_masked_email_shown_not_full_address(self):
        self.register()
        r = self.client.get(reverse("accounts:verify_email"))
        self.assertContains(r, "d***@example.com")
        self.assertNotContains(r, "dan@example.com")

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
        self.assertEqual(mail.outbox[0].subject.strip(), "Reset your Saka Keja password")
        link = re.search(r"http://\S+/accounts/password-reset/\S+/\S+/", mail.outbox[0].body).group(0)
        path = link.split("testserver")[1]
        r = self.client.get(path, follow=True)
        self.assertContains(r, "Choose a new password")
        post_url = r.redirect_chain[-1][0]
        r = self.client.post(post_url, {"new_password1": "Brand-new-pass-77", "new_password2": "Brand-new-pass-77"})
        self.assertRedirects(r, reverse("accounts:password_reset_complete"))
        self.assertTrue(self.client.login(username="sam", password="Brand-new-pass-77"))
        r = self.client.get(path, follow=True)
        self.assertContains(r, "isn't valid")

    def test_unknown_email_same_response_no_mail(self):
        r = self.client.post(reverse("accounts:password_reset"), {"email": "ghost@example.com"})
        self.assertRedirects(r, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)