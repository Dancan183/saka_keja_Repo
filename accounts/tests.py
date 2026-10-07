
import re
from datetime import timedelta
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from accounts.models import User, EmailOTP

# Create your tests here.



def code_from_outbox():
    return re.search(r"code is: (\d{6})", mail.outbox[-1].body).group(1)


class OTPFlow(TestCase):
    def register(self, role="tenant", **extra):
        data = {"username": "dan", "email": "Dan@Example.com", "phone_number": "0798907004",
                "role": role, "password1": "S3cure-pass-99", "password2": "S3cure-pass-99"}
        data.update(extra)
        return self.client.post(reverse("accounts:register"), data)

    def test_register_creates_inactive_user_and_sends_code(self):
        r = self.register()
        self.assertRedirects(r, reverse("accounts:verify_email"))
        u = User.objects.get(username="dan")
        self.assertFalse(u.is_active)
        self.assertEqual(u.email, "dan@example.com")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["dan@example.com"])
        self.assertNotIn("S3cure", mail.outbox[0].body)
        self.assertEqual(EmailOTP.objects.get().code_hash.__len__(), 64)  # hashed, not plain

    def test_unverified_cannot_login_and_gets_clear_message(self):
        self.register()
        r = self.client.post(reverse("accounts:login"), {"username": "dan", "password": "S3cure-pass-99"})
        self.assertContains(r, "not verified yet")
        r = self.client.post(reverse("accounts:login"), {"username": "dan", "password": "wrong"})
        self.assertNotContains(r, "not verified yet")

    def test_verify_success_logs_in_tenant(self):
        self.register()
        r = self.client.post(reverse("accounts:verify_email"), {"email": "dan@example.com", "code": code_from_outbox()})
        self.assertRedirects(r, reverse("properties:house_list"), fetch_redirect_response=False)
        self.assertTrue(User.objects.get(username="dan").is_active)
        self.assertIn("_auth_user_id", self.client.session)

    def test_verify_success_landlord_goes_to_add_house(self):
        self.register(role="landlord")
        r = self.client.post(reverse("accounts:verify_email"), {"email": "dan@example.com", "code": code_from_outbox()})
        self.assertRedirects(r, reverse("properties:house_create"), fetch_redirect_response=False)

    def test_wrong_code_then_lockout_after_5(self):
        self.register()
        good = code_from_outbox()
        bad = "000000" if good != "000000" else "111111"
        for _ in range(5):
            r = self.client.post(reverse("accounts:verify_email"), {"email": "dan@example.com", "code": bad})
            self.assertContains(r, "not correct")
        r = self.client.post(reverse("accounts:verify_email"), {"email": "dan@example.com", "code": good})
        self.assertContains(r, "Too many wrong attempts")
        self.assertFalse(User.objects.get(username="dan").is_active)

    def test_expired_code(self):
        self.register()
        EmailOTP.objects.update(created_at=timezone.now() - timedelta(minutes=11))
        r = self.client.post(reverse("accounts:verify_email"), {"email": "dan@example.com", "code": code_from_outbox()})
        self.assertContains(r, "expired")

    def test_code_cannot_be_reused(self):
        self.register()
        code = code_from_outbox()
        self.client.post(reverse("accounts:verify_email"), {"email": "dan@example.com", "code": code})
        User.objects.filter(username="dan").update(is_active=False)
        r = self.client.post(reverse("accounts:verify_email"), {"email": "dan@example.com", "code": code})
        self.assertContains(r, "expired")

    def test_resend_cooldown_then_new_code_invalidates_old(self):
        self.register()
        old = code_from_outbox()
        self.client.post(reverse("accounts:resend_code"), {"email": "dan@example.com"})
        self.assertEqual(len(mail.outbox), 1)  # blocked by cooldown
        EmailOTP.objects.update(created_at=timezone.now() - timedelta(minutes=2))
        self.client.post(reverse("accounts:resend_code"), {"email": "dan@example.com"})
        self.assertEqual(len(mail.outbox), 2)
        new = code_from_outbox()
        if new != old:
            r = self.client.post(reverse("accounts:verify_email"), {"email": "dan@example.com", "code": old})
            self.assertContains(r, "not correct")
        r = self.client.post(reverse("accounts:verify_email"), {"email": "dan@example.com", "code": new})
        self.assertEqual(r.status_code, 302)

    def test_resend_unknown_email_same_message_no_mail(self):
        r = self.client.post(reverse("accounts:resend_code"), {"email": "nobody@x.com"}, follow=True)
        self.assertContains(r, "If that email is waiting")
        self.assertEqual(len(mail.outbox), 0)

    def test_verify_unknown_email_generic_error(self):
        r = self.client.post(reverse("accounts:verify_email"), {"email": "nobody@x.com", "code": "123456"})
        self.assertContains(r, "not correct")

    def test_duplicate_email_rejected(self):
        self.register()
        r = self.register(username="dan2")
        self.assertContains(r, "already exists")

    def test_landlord_requires_phone(self):
        r = self.register(role="landlord", phone_number="")
        self.assertContains(r, "must provide a phone number")

    def test_pages_render(self):
        for name in ["login", "register", "verify_email", "password_reset", "password_reset_done", "password_reset_complete"]:
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
        # link is single use
        r = self.client.get(path, follow=True)
        self.assertContains(r, "isn't valid")

    def test_unknown_email_same_response_no_mail(self):
        r = self.client.post(reverse("accounts:password_reset"), {"email": "ghost@example.com"})
        self.assertRedirects(r, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_unverified_user_gets_no_reset_mail(self):
        User.objects.filter(pk=self.u.pk).update(is_active=False)
        self.client.post(reverse("accounts:password_reset"), {"email": "sam@example.com"})
        self.assertEqual(len(mail.outbox), 0)