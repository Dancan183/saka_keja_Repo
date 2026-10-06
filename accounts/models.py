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