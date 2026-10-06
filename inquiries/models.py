from django.conf import settings
from django.db import models


class Inquiry(models.Model):
    house = models.ForeignKey(
        "properties.House",
        on_delete=models.CASCADE,
        related_name="inquiries",
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_inquiries",
    )
    message = models.TextField()
    phone_number = models.CharField(
        max_length=15,
        blank=True,
        help_text="Optional. The best number for the landlord to reach you on.",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "inquiries"

    def __str__(self):
        return f"{self.tenant} about {self.house}"

    @property
    def contact_phone(self):
        """Phone given on the inquiry, falling back to the tenant's profile."""
        return self.phone_number or self.tenant.phone_number

    @property
    def whatsapp_number(self):
        """Phone in international format for wa.me links (Kenya: 07xx -> 2547xx)."""
        digits = "".join(ch for ch in self.contact_phone if ch.isdigit())
        if digits.startswith("0"):
            digits = "254" + digits[1:]
        elif digits.startswith(("7", "1")):
            digits = "254" + digits
        return digits