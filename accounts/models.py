from django.contrib.auth.models import AbstractUser
from django.db import models


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


class EmailOTP(models.Model):
    """A one-time 6-digit code sent by email. Only a hash of the code is stored."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    code_hash = models.CharField(max_length=64)
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"OTP for {self.user} ({self.created_at:%Y-%m-%d %H:%M})"