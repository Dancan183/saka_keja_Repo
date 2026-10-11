from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Role(models.TextChoices):
        TENANT = "tenant", "Tenant"
        LANDLORD = "landlord", "Landlord"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.TENANT,
    )
    phone_number = models.CharField(max_length=15, blank=True)

    @property
    def is_landlord(self):
        return self.role == self.Role.LANDLORD

    def __str__(self):
        return self.username


class PendingRegistration(models.Model):
    """
    A sign-up that is waiting for its email code.

    Nothing is written to the User table until the code is verified. This
    row holds the details temporarily (password already hashed) and is
    deleted on success or when it expires.
    """

    token = models.CharField(max_length=64, unique=True)  # also kept in the visitor's session
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150)
    password_hash = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, blank=True)
    role = models.CharField(max_length=20, choices=User.Role.choices, default=User.Role.TENANT)
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(default=0)
    code_sent_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    # The phone verification this sign-up depends on (consumed when the account is created).
    phone_token = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"Pending: {self.username} <{self.email}>"


class PhoneVerification(models.Model):
    """
    One SMS code sent to one phone number. Only a hash of the code is stored,
    and the hash also covers the phone number, so a code cannot be reused for
    another number. The token lives in the visitor's session.
    """

    token = models.CharField(max_length=64, unique=True)
    phone = models.CharField(max_length=15)          # +2547XXXXXXXX
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(default=0)
    sent_ok = models.BooleanField(default=False)     # the SMS provider accepted it
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    verified_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)  # set when the account is created

    class Meta:
        indexes = [
            models.Index(fields=["phone", "created_at"]),
            models.Index(fields=["ip_address", "created_at"]),
        ]

    def __str__(self):
        state = "consumed" if self.consumed_at else "verified" if self.verified_at else "pending"
        return f"{self.phone} ({state})"