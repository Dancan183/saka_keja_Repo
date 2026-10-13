from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Review(models.Model):
    """
    One person's review of another. Tenants review landlords, landlords review
    tenants, and only after the two have been in touch through an inquiry
    (see services.can_review). Each pair can have one review, which its author
    may edit or delete.
    """

    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_written")
    reviewee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews_received")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(max_length=500, blank=True)
    # The house the two people were in touch about (for context only).
    house = models.ForeignKey("properties.House", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    is_visible = models.BooleanField(default=True, help_text="Untick to hide this review from everyone except admins.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["reviewer", "reviewee"], name="one_review_per_pair"),
            models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name="rating_between_1_and_5"),
            models.CheckConstraint(condition=~Q(reviewer=F("reviewee")), name="no_self_review"),
        ]
        indexes = [models.Index(fields=["reviewee", "is_visible", "-created_at"])]

    def __str__(self):
        return f"{self.reviewer} rated {self.reviewee} {self.rating}/5"


class ReviewReport(models.Model):
    """A user flagging a review for the admins to look at. Reports never hide a review by themselves."""

    class Reason(models.TextChoices):
        FAKE = "fake", "Fake or never dealt with this person"
        ABUSIVE = "abusive", "Abusive or offensive"
        PRIVATE = "private", "Shares private information"
        OTHER = "other", "Something else"

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_reports")
    reason = models.CharField(max_length=20, choices=Reason.choices)
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["review", "reporter"], name="one_report_per_user_per_review")]

    def __str__(self):
        return f"Report on review {self.review_id}: {self.reason}"